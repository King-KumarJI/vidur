// VIDUR Specs Module -- Environmental Sensor Firmware
// (ESP32 + Arduino Uno / Nano / Mega 2560, one shared codebase)
//
// Implements the protocol documented in docs/specs/serial-protocol.md
// (already relied on by backend/scripts/local_agent.py's hardware read
// path -- no changes to that file's READ/response contract were needed
// for this firmware to work with it):
//
//   - USB CDC serial, 115200 8N1, line-based ASCII, "\n"-terminated.
//   - Agent sends the literal line "READ". Firmware responds with
//     exactly one line of flat JSON containing whichever of the four
//     metric keys it can currently read: temperature_celsius,
//     humidity_percent, ambient_light_lux, noise_level_db. A key is
//     OMITTED (never fabricated, never a stale value, never zero) when
//     that sensor's reading fails or isn't physically present -- the
//     agent then reports that field as `status: "missing"` for that
//     cycle only.
//   - Agent sends the literal line "IDENTIFY" (protocol v1.1 addition,
//     see serial-protocol.md's "Board identification handshake"
//     section). Firmware responds with exactly one line of flat JSON:
//     {"board": "<id>"}, where <id> is one of "esp32", "uno", "nano",
//     "mega2560" -- this is the authoritative confirmation that real
//     VIDUR firmware (not some unrelated device sharing the same
//     CH340/CP210x/FTDI USB-serial chip) is actually listening, and
//     which board it's running on.
//   - The firmware never sends anything unsolicited; it only answers a
//     "READ" or "IDENTIFY" request. Any other line is silently ignored.
//
// One shared codebase compiles for four PlatformIO environments (see
// platformio.ini): esp32dev, uno, nanoatmega328new, megaatmega2560. The
// sensor wiring (DHT22 temperature/humidity on a digital pin, BH1750
// ambient light on I2C, an analog sound sensor module on an ADC pin)
// and the READ/IDENTIFY protocol logic are identical across all four
// targets -- #ifdef is used only where the underlying hardware truly
// differs (ESP32's configurable I2C pins and 12-bit ADC vs. AVR's
// fixed-in-silicon I2C pins and 10-bit ADC). See firmware/README.md for
// the full per-board wiring table.
//
// Arduino Uno/Nano's ATmega328P has only 2KB of SRAM, so this firmware
// deliberately avoids the Arduino String class (which heap-allocates
// and fragments) for both the request parser and the JSON response
// builder, using fixed-size char buffers, dtostrf(), and snprintf()
// instead -- see handleReadRequest()/handleIdentifyRequest() and the
// loop() command parser below. This also avoids relying on AVR's
// snprintf() supporting "%f" directly, which the default Arduino AVR
// toolchain does NOT link in (a well-known AVR-libc gotcha) --
// dtostrf() converts each float to text first, then snprintf() only
// ever formats "%s" strings.
//
// VERIFICATION STATUS (VIDUR Constitution Article 50-51, No Fake
// Completion Law): this firmware is COMPILE-VERIFIED ONLY, via
// `pio run -e <environment>` against all four board targets. No
// physical ESP32, Uno, Nano, Mega, DHT22, BH1750, or sound sensor
// module was available in this environment, so NONE of the sensor
// reads or the IDENTIFY/READ handshake below have been exercised
// against real hardware on any board. Do not treat this file as
// hardware-verified until it has actually been flashed and tested.

#include <Arduino.h>
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>
#include <string.h>

// ---------------------------------------------------------------------
// Board identification. VIDUR_BOARD_ID is supplied by each PlatformIO
// environment's build_flags (see platformio.ini) rather than inferred
// from Arduino-core-internal board macros -- the mapping from
// PlatformIO environment -> IDENTIFY response lives in exactly one
// place and is explicit, not guessed.
// ---------------------------------------------------------------------

#ifndef VIDUR_BOARD_ID
#error "VIDUR_BOARD_ID is not defined -- build via one of platformio.ini's environments (esp32dev, uno, nanoatmega328new, megaatmega2560), not a bare compiler invocation."
#endif

// ---------------------------------------------------------------------
// Pin configuration -- see firmware/README.md for the matching wiring
// diagram (one row per board).
//
// The only *behavioral* (not just label) difference between targets is
// ESP32 vs. AVR: Uno/Nano/Mega all share identical AVR behavior --
// Wire.begin() takes no pin arguments because I2C SDA/SCL are fixed in
// silicon per chip (not configurable in software), and analogRead() is
// a 10-bit ADC. The physical I2C pins differ *by board* (Uno/Nano:
// A4/A5; Mega: pins 20/21) but that is a wiring fact, not a code
// difference -- Wire.begin() is called identically either way. This is
// why one AVR branch below covers all three AVR boards.
// ---------------------------------------------------------------------

constexpr uint8_t DHT_PIN = 4;  // DHT22 data line, digital pin 4 on every
                                 // supported board (needs a 10k pull-up
                                 // to the sensor's VCC per its datasheet,
                                 // unless the breakout already has one).
constexpr uint8_t DHT_SENSOR_TYPE = DHT22;

#if defined(ARDUINO_ARCH_ESP32)
constexpr uint8_t I2C_SDA_PIN = 21;    // ESP32 Arduino core's default I2C SDA pin.
constexpr uint8_t I2C_SCL_PIN = 22;    // ESP32 Arduino core's default I2C SCL pin.
constexpr uint8_t SOUND_ADC_PIN = 34;  // ADC1_CH6 -- input-only pin, safe
                                        // to read while Wi-Fi/ADC2 is used
                                        // elsewhere.
constexpr float ADC_MAX_VALUE = 4095.0f;  // ESP32 ADC: 12-bit.
#else
// AVR (Uno / Nano / Mega): I2C pins are fixed in silicon (Uno/Nano:
// A4=SDA/A5=SCL; Mega: pin 20=SDA/pin 21=SCL) -- Wire.begin() below
// takes no pin arguments regardless of which AVR board this is.
constexpr uint8_t SOUND_ADC_PIN = A0;
constexpr float ADC_MAX_VALUE = 1023.0f;  // AVR ADC: 10-bit.
#endif

constexpr unsigned long SERIAL_BAUD_RATE = 115200;
constexpr unsigned long SERIAL_READ_TIMEOUT_MS = 1000;

DHT dhtSensor(DHT_PIN, DHT_SENSOR_TYPE);
BH1750 lightSensor;

// ---------------------------------------------------------------------
// Sound sensor: native analogRead() only, no extra library (identical
// on every supported board -- only the pin and ADC resolution differ,
// both already captured by SOUND_ADC_PIN/ADC_MAX_VALUE above). Most
// low-cost analog sound sensor modules (electret mic + op-amp/
// comparator board) output a voltage envelope proportional to sound
// pressure, not a lab-calibrated dB(SPL) value. This linear map from
// the averaged raw ADC reading to an approximate dB range is a
// documented approximation for a plausible "quiet room" -> "loud room"
// span; it is NOT a calibrated sound level meter and its accuracy
// depends entirely on the specific module wired up. Averaging several
// samples smooths out single-sample electrical noise on the ADC line.
// ---------------------------------------------------------------------

constexpr int SOUND_SAMPLE_COUNT = 32;
constexpr float SOUND_DB_MIN = 30.0f;  // Approx. quiet-room floor.
constexpr float SOUND_DB_MAX = 100.0f; // Approx. loud-room ceiling.

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
//
// Deliberately avoids the Arduino String class (see file header) --
// the JSON response is hand-built into a fixed-size stack buffer using
// dtostrf() (float -> text, works identically on AVR and ESP32 cores)
// plus snprintf() formatting only "%s" (never "%f", which AVR's default
// snprintf() does not support).
// ---------------------------------------------------------------------

constexpr size_t JSON_RESPONSE_BUFFER_SIZE = 128;
constexpr size_t FLOAT_TEXT_BUFFER_SIZE = 16;

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
  // check -- it is always considered available on every supported board.
  float noiseLevelDb = readNoiseLevelDb();

  char jsonBuffer[JSON_RESPONSE_BUFFER_SIZE];
  char floatText[FLOAT_TEXT_BUFFER_SIZE];
  size_t length = 0;
  bool wroteAnyField = false;

  jsonBuffer[length++] = '{';

  if (temperatureHumidityAvailable) {
    dtostrf(temperatureCelsius, 0, 1, floatText);
    length += snprintf(jsonBuffer + length, JSON_RESPONSE_BUFFER_SIZE - length,
                        "\"temperature_celsius\":%s", floatText);
    dtostrf(humidityPercent, 0, 1, floatText);
    length += snprintf(jsonBuffer + length, JSON_RESPONSE_BUFFER_SIZE - length,
                        ",\"humidity_percent\":%s", floatText);
    wroteAnyField = true;
  }

  if (ambientLightAvailable) {
    dtostrf(ambientLightLux, 0, 1, floatText);
    length += snprintf(jsonBuffer + length, JSON_RESPONSE_BUFFER_SIZE - length,
                        "%s\"ambient_light_lux\":%s", wroteAnyField ? "," : "", floatText);
    wroteAnyField = true;
  }

  dtostrf(noiseLevelDb, 0, 1, floatText);
  length += snprintf(jsonBuffer + length, JSON_RESPONSE_BUFFER_SIZE - length,
                      "%s\"noise_level_db\":%s", wroteAnyField ? "," : "", floatText);

  snprintf(jsonBuffer + length, JSON_RESPONSE_BUFFER_SIZE - length, "}");

  Serial.println(jsonBuffer);
}

// Builds and sends the single JSON response line for one "IDENTIFY"
// request: {"board": "<id>"}. VIDUR_BOARD_ID is a compile-time string
// literal (see platformio.ini), so this can be a flash-resident literal
// (F()) rather than anything built at runtime -- important on Uno/Nano's
// 2KB of SRAM.
void handleIdentifyRequest() {
  Serial.println(F("{\"board\":\"" VIDUR_BOARD_ID "\"}"));
}

// ---------------------------------------------------------------------
// Command parsing -- a fixed-size buffer, never Arduino String, so this
// firmware has a bounded, predictable RAM footprint on Uno/Nano's 2KB
// of SRAM regardless of how much or how little serial traffic arrives.
// ---------------------------------------------------------------------

constexpr size_t COMMAND_BUFFER_SIZE = 16;  // "IDENTIFY" is the longest
                                             // defined command (8 chars);
                                             // this leaves headroom.
char commandBuffer[COMMAND_BUFFER_SIZE];
uint8_t commandLength = 0;

const char *const READ_COMMAND = "READ";
const char *const IDENTIFY_COMMAND = "IDENTIFY";

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.setTimeout(SERIAL_READ_TIMEOUT_MS);

  dhtSensor.begin();

#if defined(ARDUINO_ARCH_ESP32)
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
#else
  Wire.begin();  // AVR: SDA/SCL are fixed in silicon, no pin arguments.
#endif
  lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);

  // ADC width/attenuation defaults (ESP32: 12-bit, 0-3.3V full scale via
  // ADC_11db; AVR: 10-bit, 0-5V or 0-3.3V depending on board voltage)
  // are each core's Arduino defaults and are left unchanged.
}

void loop() {
  while (Serial.available() > 0) {
    char incomingChar = static_cast<char>(Serial.read());

    if (incomingChar == '\n') {
      // Strip a trailing '\r' left by a "\r\n"-terminated sender, per
      // serial-protocol.md's "\r\n accepted, stripped on read".
      if (commandLength > 0 && commandBuffer[commandLength - 1] == '\r') {
        commandLength--;
      }
      commandBuffer[commandLength] = '\0';

      if (strcmp(commandBuffer, READ_COMMAND) == 0) {
        handleReadRequest();
      } else if (strcmp(commandBuffer, IDENTIFY_COMMAND) == 0) {
        handleIdentifyRequest();
      }
      // Any other line -- including one that overflowed
      // COMMAND_BUFFER_SIZE and was silently truncated below -- is
      // ignored, per "no other request verbs exist in this version of
      // the protocol" and "the firmware never sends anything
      // unsolicited".

      commandLength = 0;
    } else if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = incomingChar;
    }
    // else: the line so far exceeds COMMAND_BUFFER_SIZE - 1 characters;
    // extra characters before the next '\n' are dropped rather than
    // overflowing the buffer. The resulting truncated command will not
    // match READ_COMMAND/IDENTIFY_COMMAND and is harmlessly ignored.
  }
}
