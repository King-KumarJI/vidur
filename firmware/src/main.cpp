// VIDUR Specs Module -- Environmental Sensor Firmware (ESP32)
//
// Implements exactly the protocol documented in
// docs/specs/serial-protocol.md (already relied on by
// backend/scripts/local_agent.py's hardware read path -- no changes to
// that file are needed for this firmware to work with it):
//
//   - USB CDC serial, 115200 8N1, line-based ASCII, "\n"-terminated.
//   - Agent sends the literal line "READ". No other request verbs exist.
//   - Firmware responds with exactly one line of flat JSON containing
//     whichever of the four metric keys it can currently read:
//     temperature_celsius, humidity_percent, ambient_light_lux,
//     noise_level_db. A key is OMITTED (never fabricated, never a stale
//     value, never zero) when that sensor's reading fails or isn't
//     physically present -- the agent then reports that field as
//     `status: "missing"` for that cycle only.
//   - The firmware never sends anything unsolicited; it only answers a
//     "READ" request.
//
// Target board for this session: a generic ESP32 dev board with a DHT22
// (temperature/humidity, digital pin), a BH1750 (ambient light, I2C),
// and an analog sound sensor module (ADC pin). See firmware/README.md
// for wiring.
//
// VERIFICATION STATUS (VIDUR Constitution Article 50-51, No Fake
// Completion Law): this firmware is COMPILE-VERIFIED ONLY via
// `pio run` against the esp32dev target. No physical ESP32, DHT22,
// BH1750, or sound sensor module was available in this environment, so
// NONE of the sensor reads below have been exercised against real
// hardware. Do not treat this file as hardware-verified until it has
// actually been flashed and tested on a real board.

#include <Arduino.h>
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>

// ---------------------------------------------------------------------
// Pin configuration -- see firmware/README.md for the matching wiring
// diagram.
// ---------------------------------------------------------------------

constexpr uint8_t DHT_PIN = 4;       // DHT22 data line (digital, needs a
                                     // 10k pull-up to 3V3 per the sensor's
                                     // datasheet).
constexpr uint8_t DHT_SENSOR_TYPE = DHT22;

constexpr uint8_t I2C_SDA_PIN = 21;  // BH1750 SDA (ESP32 default I2C pins).
constexpr uint8_t I2C_SCL_PIN = 22;  // BH1750 SCL.

constexpr uint8_t SOUND_ADC_PIN = 34; // Analog sound sensor module output
                                       // (ADC1_CH6 -- input-only pin, safe
                                       // to read while Wi-Fi/ADC2 is used
                                       // elsewhere).

constexpr unsigned long SERIAL_BAUD_RATE = 115200;
constexpr unsigned long SERIAL_READ_TIMEOUT_MS = 1000;

const char *const REQUEST_LINE = "READ";

DHT dhtSensor(DHT_PIN, DHT_SENSOR_TYPE);
BH1750 lightSensor;

// ---------------------------------------------------------------------
// Sound sensor: native analogRead() only, per the task's explicit
// instruction (no extra library). Most low-cost analog sound sensor
// modules (electret mic + op-amp/comparator board) output a voltage
// envelope proportional to sound pressure, not a lab-calibrated dB(SPL)
// value. This linear map from the averaged raw ADC reading to an
// approximate dB range is a documented approximation for a plausible
// "quiet room" -> "loud room" span; it is NOT a calibrated sound level
// meter and its accuracy depends entirely on the specific module wired
// up. Averaging several samples smooths out single-sample electrical
// noise on the ADC line.
// ---------------------------------------------------------------------

constexpr int SOUND_SAMPLE_COUNT = 32;
constexpr float ADC_MAX_VALUE = 4095.0f; // ESP32 ADC default: 12-bit.
constexpr float SOUND_DB_MIN = 30.0f;    // Approx. quiet-room floor.
constexpr float SOUND_DB_MAX = 100.0f;   // Approx. loud-room ceiling.

float readNoiseLevelDb() {
  long sampleSum = 0;
  for (int sampleIndex = 0; sampleIndex < SOUND_SAMPLE_COUNT; sampleIndex++) {
    sampleSum += analogRead(SOUND_ADC_PIN);
    delayMicroseconds(200);
  }
  float averageRawReading = static_cast<float>(sampleSum) / SOUND_SAMPLE_COUNT;
  float normalizedLevel = averageRawReading / ADC_MAX_VALUE;
  if (normalizedLevel < 0.0f) {
    normalizedLevel = 0.0f;
  } else if (normalizedLevel > 1.0f) {
    normalizedLevel = 1.0f;
  }
  return SOUND_DB_MIN + normalizedLevel * (SOUND_DB_MAX - SOUND_DB_MIN);
}

// ---------------------------------------------------------------------
// Request handling
// ---------------------------------------------------------------------

// Builds and sends the single JSON response line for one "READ" request.
// Each sensor is read fresh on every request (no caching of a prior
// reading), and each metric key is only written into the JSON object if
// that specific read succeeded this cycle -- a failed or absent sensor's
// key is omitted entirely, per serial-protocol.md's per-sensor-presence
// rule.
void handleReadRequest() {
  // DHT22 reports temperature and humidity from a single digital read;
  // the Adafruit library returns NaN for either value when that read
  // glitches (common for this sensor family under bus-timing jitter).
  // Treat the whole read as failed and omit BOTH keys together rather
  // than pairing one good value with a stale/fabricated partner --
  // there is no way to independently verify just one of the two.
  float temperatureCelsius = dhtSensor.readTemperature();
  float humidityPercent = dhtSensor.readHumidity();
  bool temperatureHumidityAvailable =
      !isnan(temperatureCelsius) && !isnan(humidityPercent);

  // BH1750's library returns a negative value on an I2C read error.
  float ambientLightLux = lightSensor.readLightLevel();
  bool ambientLightAvailable = ambientLightLux >= 0.0f;

  // The sound sensor is native analogRead() with no failure signal to
  // check -- it is always considered available on this board.
  float noiseLevelDb = readNoiseLevelDb();

  String jsonLine = "{";
  bool wroteAnyField = false;

  if (temperatureHumidityAvailable) {
    jsonLine += "\"temperature_celsius\":" + String(temperatureCelsius, 1);
    jsonLine += ",\"humidity_percent\":" + String(humidityPercent, 1);
    wroteAnyField = true;
  }

  if (ambientLightAvailable) {
    if (wroteAnyField) {
      jsonLine += ",";
    }
    jsonLine += "\"ambient_light_lux\":" + String(ambientLightLux, 1);
    wroteAnyField = true;
  }

  if (wroteAnyField) {
    jsonLine += ",";
  }
  jsonLine += "\"noise_level_db\":" + String(noiseLevelDb, 1);

  jsonLine += "}";

  Serial.println(jsonLine);
}

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.setTimeout(SERIAL_READ_TIMEOUT_MS);

  dhtSensor.begin();

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);

  // ADC width/attenuation defaults (12-bit, 0-3.3V full scale via
  // ADC_11db) are the ESP32 Arduino core's defaults and are left
  // unchanged -- no analogReadResolution()/analogSetAttenuation() calls
  // needed for this sensor module.
}

void loop() {
  if (Serial.available() > 0) {
    String receivedLine = Serial.readStringUntil('\n');
    receivedLine.trim(); // Strips a trailing '\r' and surrounding whitespace.

    if (receivedLine == REQUEST_LINE) {
      handleReadRequest();
    }
    // Any other request verb is silently ignored: per
    // serial-protocol.md, "No other request verbs exist in this
    // version of the protocol," and the firmware must never send
    // anything unsolicited.
  }
}
