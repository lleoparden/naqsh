// Clean Group 3 review screenshots: home in clean mode, editor on the menu job.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const OUT = "L:/naqsh-review/group3";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
for (const [w, h] of [[1440, 900], [1920, 1080]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/polish-${w}-home.png` });

  await page.goto(`${BASE}/?job=e13f9585b24f`, { waitUntil: "networkidle" });
  await page.waitForSelector("svg text");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/polish-${w}-editor.png` });
  await page.close();
}
await browser.close();
console.log("clean polish screenshots written");
