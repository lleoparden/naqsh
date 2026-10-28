// Reproduce the on-screen after-side offset at exactly 100% zoom and DPR 1/2.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const JOB = "d3dbface16b8";
const OUT = "L:/naqsh-review/offset";
fs.mkdirSync(OUT, { recursive: true });

const results = [];
for (const dpr of [1.25, 1.5]) {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  // Sized so the fit calculation lands exactly on 100%.
  const page = await browser.newPage({ viewport: { width: 1708, height: 2060 }, deviceScaleFactor: dpr });
  await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
  await page.waitForSelector("svg text");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const zoom = await page.getByTestId("zoom-level").textContent();

  const range = page.getByLabel("Before and after reveal");
  const setSplit = async (value) => {
    await range.evaluate((el, v) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(el, String(v));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }, value);
    await page.waitForTimeout(350);
  };

  const canvas = page.locator('[data-testid="canvas-svg"]');
  for (const value of [100, 0]) {
    await setSplit(value);
    await canvas.screenshot({ path: `${OUT}/exact-dpr${dpr}-${value}.png` });
  }
  results.push({ dpr, zoom });
  await browser.close();
}

fs.writeFileSync(`${OUT}/exact.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results));
