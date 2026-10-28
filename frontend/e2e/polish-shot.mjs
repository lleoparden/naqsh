// Polish screenshots at 1440x900 and 1920x1080: home, editor, loading and empty states.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const OUT = "L:/naqsh-review/group3";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
for (const [w, h] of [[1440, 900], [1920, 1080]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/polish-${w}-home.png` });

  await page.goto(`${BASE}/?job=d3dbface16b8`, { waitUntil: "networkidle" });
  await page.waitForSelector("svg text");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/polish-${w}-editor.png` });

  await page.goto(`${BASE}/?job=missing-job`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/polish-${w}-loading.png` });
  await page.close();
}
await browser.close();
console.log("polish screenshots written");
