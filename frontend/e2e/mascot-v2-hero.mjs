// 1080 px hero frames for four states, 24 fps.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SVG = fs.readFileSync("L:/naqsh/assets/mascot/naqsh-v2.svg", "utf8");
const OUT = "L:/naqsh-review/mascot-assets/v2/frames/1080";
const STATES = { idle: 36, talking: 36, happy: 24, excited: 24 };

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: CHROME, headless: true });
for (const [state, count] of Object.entries(STATES)) {
  const dir = `${OUT}/${state}`;
  fs.mkdirSync(dir, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 } });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setContent(
    `<style>html,body{margin:0;background:transparent}svg{width:1080px;height:1080px;display:block}</style>` +
      SVG.replace('class="mascot-v2 state-idle"', `class="mascot-v2 state-${state}"`),
  );
  await page.waitForTimeout(120);
  for (let frame = 0; frame < count; frame++) {
    const time = (frame * 1000) / 24;
    await page.evaluate((t) => {
      for (const animation of document.getAnimations()) {
        animation.pause();
        animation.currentTime = t;
      }
    }, time);
    await page.screenshot({ path: `${dir}/frame-${String(frame).padStart(3, "0")}.png`, omitBackground: true });
  }
  await page.close();
  console.log(state, count);
}
await browser.close();
