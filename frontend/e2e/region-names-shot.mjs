// Evidence for AI region names: layer list shows descriptive names, not t1/t2.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const OUT = "L:/naqsh-review/group3";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const results = [];
for (const [name, job] of [["comic", "d3dbface16b8"], ["menu", "e13f9585b24f"]]) {
  await page.goto(`${BASE}/?job=${job}`, { waitUntil: "networkidle" });
  await page.waitForSelector("svg text");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const list = (await page.locator('[data-testid="layers-list"]').textContent()) || "";
  const named = !list.includes("t1 ·") && (list.includes("title") || list.includes("speech") || list.includes("banner"));
  results.push({ page: name, named, list: list.slice(0, 220) });
  await page.screenshot({ path: `${OUT}/region-names-${name}.png` });
  console.log(name, named, list.slice(0, 120));
}
fs.writeFileSync(`${OUT}/region-names.json`, JSON.stringify(results, null, 2));
await browser.close();
process.exit(results.every((item) => item.named) ? 0 : 1);
