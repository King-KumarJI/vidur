import { chromium } from 'playwright'

const errors = []
const browser = await chromium.launch()
const page = await browser.newPage()
page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push(msg.text())
})
page.on('pageerror', (err) => errors.push(String(err)))

await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
await page.waitForSelector('text=Dashboard', { timeout: 10000 })
await page.screenshot({ path: '.smoketest-dashboard.png', fullPage: true })

// Exercise the project switcher: validate + set an active project.
await page.click('button:has-text("No project selected")')
await page.fill('input[placeholder="project-id"]', 'demo-project')
await page.click('button:has-text("Set")')
await page.waitForSelector('text=demo-project', { timeout: 10000 })
await page.screenshot({ path: '.smoketest-project-switched.png', fullPage: true })

// Navigate to a project-scoped page and confirm it renders its form.
await page.click('text=Inspection Reports')
await page.waitForSelector('input[placeholder^="Absolute path"]', { timeout: 10000 })
await page.screenshot({ path: '.smoketest-inspection.png', fullPage: true })

// Navigate to ML Prediction (Major-tier, flag disabled) and confirm the
// page renders without crashing.
await page.click('text=ML Prediction')
await page.waitForSelector('text=MAJOR_ML_RISK_PREDICTION', { timeout: 10000 })
await page.screenshot({ path: '.smoketest-ml-prediction.png', fullPage: true })

// Settings/feature flags page.
await page.click('text=Feature Flags / Settings')
await page.waitForSelector('text=MINOR_PROJECT_INSPECTION', { timeout: 10000 })
await page.screenshot({ path: '.smoketest-settings.png', fullPage: true })

await browser.close()

console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
if (errors.length > 0) process.exit(1)
