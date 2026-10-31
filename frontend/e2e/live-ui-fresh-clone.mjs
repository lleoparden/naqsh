// Live UI run in the fresh clone: upload one comic, wait for the result, open the editor.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
const OUT = "L:/naqsh-review/live-ui";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
let receipt = null;
page.on("response", async (response) => {
  if (response.url().includes("/api/localize") && response.request().method() === "POST") {
    try { receipt = await response.json(); } catch { /* ignore */ }
  }
});

await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
const started = Date.now();
await page.setInputFiles('input[type="file"]', FIXTURE);
await page.waitForSelector('a:has-text("Open editor")', { timeout: 300000 });
const seconds = (Date.now() - started) / 1000;
await page.screenshot({ path: `${OUT}/result.png` });
await page.getByRole("link", { name: "Open editor" }).click();
await page.waitForSelector("svg text");
await page.waitForTimeout(500);
await page.screenshot({ path: `${OUT}/editor.png` });
const layers = await page.locator('[data-testid="layers-list"]').textContent();
fs.writeFileSync(`${OUT}/live-ui.json`, JSON.stringify({ receipt, seconds, layers: (layers || "").slice(0, 400), errors }, null, 2));
console.log(JSON.stringify({ id: receipt?.id, total_ms: receipt?.total_ms, cost: receipt?.total_cost_usd, wall_seconds: seconds, demo: receipt?.demo, errors }, null, 2));
await browser.close();
