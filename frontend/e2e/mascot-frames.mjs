// Deterministic 12 fps frames for each mascot state, at 512 px with alpha.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SVG = fs.readFileSync("L:/naqsh/assets/mascot/naqsh.svg", "utf8");
const OUT = "L:/naqsh-review/mascot-assets/frames";
const STATES = { idle: 24, thinking: 24, wave: 18, happy: 18, sad: 18 };
const FPS = 12;

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: CHROME, headless: true });
for (const [state, count] of Object.entries(STATES)) {
  const dir = `${OUT}/${state}`;
  fs.mkdirSync(dir, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: 1 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setContent(
    `<style>html,body{margin:0;background:transparent}svg{width:512px;height:512px;display:block}</style>` +
      SVG.replace('class="mascot-svg state-idle"', `class="mascot-svg state-${state}"`),
  );
  await page.waitForTimeout(120);
  for (let frame = 0; frame < count; frame++) {
    const time = (frame * 1000) / FPS;
    await page.evaluate((t) => {
      for (const animation of document.getAnimations()) {
        animation.pause();
        animation.currentTime = t;
      }
    }, time);
    await page.screenshot({ path: `${dir}/frame-${String(frame).padStart(3, "0")}.png`, omitBackground: true });
  }
  // Seam frame at exactly one period; compare to frame 0 in the verifier.
  await page.evaluate((t) => {
    for (const animation of document.getAnimations()) {
      animation.pause();
      animation.currentTime = t;
    }
  }, (count * 1000) / FPS);
  await page.screenshot({ path: `${dir}/seam.png`, omitBackground: true });
  await page.close();
  console.log(state, count);
}
await browser.close();
