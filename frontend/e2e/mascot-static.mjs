// Static mascot poses: 512 px transparent per state + 1024 px idle.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SVG = fs.readFileSync("L:/naqsh/assets/mascot/naqsh.svg", "utf8");
const OUT = "L:/naqsh-review/mascot-assets/static";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
for (const state of ["idle", "thinking", "wave", "happy", "sad"]) {
  const page = await browser.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: 1 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setContent(
    `<style>html,body{margin:0;background:transparent}svg{width:512px;height:512px;display:block}</style>` +
      SVG.replace('class="mascot-svg state-idle"', `class="mascot-svg state-${state}"`),
  );
  await page.waitForTimeout(150);
  await page.screenshot({ path: `${OUT}/naqsh-${state}-512.png`, omitBackground: true });
  await page.close();
}
const page = await browser.newPage({ viewport: { width: 1024, height: 1024 }, deviceScaleFactor: 1 });
await page.emulateMedia({ reducedMotion: "reduce" });
await page.setContent(
  `<style>html,body{margin:0;background:transparent}svg{width:1024px;height:1024px;display:block}</style>` + SVG,
);
await page.waitForTimeout(150);
await page.screenshot({ path: `${OUT}/naqsh-idle-1024.png`, omitBackground: true });
await page.close();
await browser.close();
console.log("static poses written");
