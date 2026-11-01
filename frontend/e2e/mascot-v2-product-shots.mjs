// v2 product-state screenshots at 1440x900 and 1920x1080.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
const OUT = "L:/naqsh-review/mascot-product-v2";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
async function pageAt(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
  return page;
}

for (const [width, height] of [[1440, 900], [1920, 1080]]) {
  let page = await pageAt(width, height);
  await page.waitForSelector(".mascot svg");
  await page.screenshot({ path: `${OUT}/${width}-idle.png` });
  await page.hover(".mascot");
  await page.waitForTimeout(350);
  await page.screenshot({ path: `${OUT}/${width}-wave.png` });
  await page.close();

  page = await pageAt(width, height);
  await page.route("**/api/localize", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await page.setInputFiles('input[type="file"]', FIXTURE);
  await page.waitForSelector("text=Localizing your page", { timeout: 10000 });
  await page.screenshot({ path: `${OUT}/${width}-thinking.png` });
  await page.waitForSelector("text=Page localized", { timeout: 120000 });
  await page.waitForSelector("text=Replaying recorded stages at their real pace", { state: "detached", timeout: 180000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/${width}-happy.png` });
  await page.close();

  page = await pageAt(width, height);
  await page.route("**/api/localize", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "test failure" }) }),
  );
  await page.setInputFiles('input[type="file"]', FIXTURE);
  await page.waitForSelector("text=Something went wrong", { timeout: 10000 });
  await page.screenshot({ path: `${OUT}/${width}-sad.png` });
  await page.close();
}
await browser.close();
console.log("v2 product screenshots written");
