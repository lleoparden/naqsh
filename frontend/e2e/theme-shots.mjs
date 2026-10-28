// No model calls: this script only uses document/layout/reset/cover/export endpoints.
// Theme screenshots at 1440x900.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const OUT = "L:/naqsh-review/theme";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

await page.goto(`${BASE}/?job=d3dbface16b8`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.locator("aside button", { hasText: "t1" }).first().click();
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/editor-1440.png` });

await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/home-1440.png` });

const colors = await page.evaluate(() => {
  const body = getComputedStyle(document.body);
  const button = document.querySelector("button");
  return {
    bodyBg: body.backgroundColor,
    bodyColor: body.color,
    bodyFont: body.fontFamily,
    buttonBg: button ? getComputedStyle(button).backgroundColor : null,
  };
});
fs.writeFileSync(`${OUT}/theme.json`, JSON.stringify(colors, null, 2));
console.log(JSON.stringify(colors));
await browser.close();
