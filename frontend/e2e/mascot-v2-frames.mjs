// Deterministic v2 frames: every state at 24 fps and 12 fps, 768 px, alpha.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SVG = fs.readFileSync("L:/naqsh/assets/mascot/naqsh-v2.svg", "utf8");
const OUT = "L:/naqsh-review/mascot-assets/v2/frames";
const LOOPS = ["idle", "talking", "thinking", "laughing", "sleepy", "working"];
const STATES = [
  ...LOOPS,
  "blink", "curious", "surprised", "confused", "happy", "excited", "proud", "sad", "wave-hello", "wave-goodbye",
];
const FPS = { 24: 24, 12: 12 };

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: CHROME, headless: true });

for (const fps of [24, 12]) {
  for (const state of STATES) {
    const count = (LOOPS.includes(state) ? 1.5 : 1) * fps;
    const dir = `${OUT}/${fps}fps/${state}`;
    fs.mkdirSync(dir, { recursive: true });
    const page = await browser.newPage({ viewport: { width: 768, height: 768 }, deviceScaleFactor: 1 });
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.setContent(
      `<style>html,body{margin:0;background:transparent}svg{width:768px;height:768px;display:block}</style>` +
        SVG.replace('class="mascot-v2 state-idle"', `class="mascot-v2 state-${state}"`),
    );
    await page.waitForTimeout(120);
    for (let frame = 0; frame < count; frame++) {
      const time = (frame * 1000) / fps;
      await page.evaluate((t) => {
        for (const animation of document.getAnimations()) {
          animation.pause();
          animation.currentTime = t;
        }
      }, time);
      await page.screenshot({ path: `${dir}/frame-${String(frame).padStart(3, "0")}.png`, omitBackground: true });
    }
    if (LOOPS.includes(state)) {
      await page.evaluate((t) => {
        for (const animation of document.getAnimations()) {
          animation.pause();
          animation.currentTime = t;
        }
      }, (count * 1000) / fps);
      await page.screenshot({ path: `${dir}/seam.png`, omitBackground: true });
    }
    await page.close();
    console.log(fps, state, count);
  }
}
await browser.close();
