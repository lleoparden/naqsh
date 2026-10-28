// Reproduce the on-screen after-side offset at 100% zoom.
// Captures the canvas element at split 100 (all before), 50 and 0 (all after).
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const JOB = "d3dbface16b8";
const OUT = "L:/naqsh-review/offset";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.keyboard.press("Escape");

// Zoom to 100% (buttons step by 10%).
for (let i = 0; i < 15; i += 1) {
  const text = (await page.getByTestId("zoom-level").textContent()) || "0%";
  if (Number(text.replace("%", "")) >= 100) break;
  await page.getByRole("button", { name: "Zoom in" }).click();
}
await page.waitForTimeout(500);
const zoom = await page.getByTestId("zoom-level").textContent();

const range = page.getByLabel("Before and after reveal");
const setSplit = async (value) => {
  await range.evaluate((el, v) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(el, String(v));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  await page.waitForTimeout(300);
};

const canvas = page.locator('[data-testid="canvas-svg"]');
for (const value of [100, 50, 0]) {
  await setSplit(value);
  await canvas.screenshot({ path: `${OUT}/canvas-${value}.png` });
}

fs.writeFileSync(`${OUT}/offset.json`, JSON.stringify({ zoom, job: JOB, viewport: "1600x1000", dpr: 1 }, null, 2));
console.log(JSON.stringify({ zoom }));
await browser.close();
