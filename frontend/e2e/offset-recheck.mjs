// Re-check the reported after-side offset at exactly 100% zoom, Original on/off and
// slider positions 0/50/100. Saves canvas screenshots and the server PNG export.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const OUT = "L:/naqsh-review/offset";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
fs.mkdirSync(OUT, { recursive: true });

const upload = process.env.JOB
  ? null
  : await fetch(`${API}/api/localize`, {
      method: "POST",
      body: (() => {
        const data = new FormData();
        data.append("image", new Blob([fs.readFileSync(FIXTURE)], { type: "image/png" }), "comic.png");
        data.append("register", "egyptian");
        return data;
      })(),
    });
const receipt = upload ? await upload.json() : { id: process.env.JOB, demo: false };
console.log("job", receipt.id, "demo", receipt.demo);

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1742, height: 2058 }, deviceScaleFactor: 1 });
await page.goto(`${BASE}/?job=${receipt.id}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.keyboard.press("Escape");
await page.waitForTimeout(500);

const zoom = await page.getByTestId("zoom-level").textContent();
const canvas = page.locator('[data-testid="canvas-svg"]');
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

await setSplit(100);
await canvas.screenshot({ path: `${OUT}/orig-on-split-100.png` });
await page.getByRole("button", { name: "Original" }).click();
await page.waitForTimeout(400);
await canvas.screenshot({ path: `${OUT}/original-toggle-on.png` });
await page.getByRole("button", { name: "Original" }).click();
await page.waitForTimeout(400);
await setSplit(0);
await canvas.screenshot({ path: `${OUT}/after-split-0.png` });
await setSplit(50);
await canvas.screenshot({ path: `${OUT}/split-50.png` });
await setSplit(100);
await canvas.screenshot({ path: `${OUT}/before-split-100.png` });

const png = await fetch(`${API}/api/jobs/${receipt.id}/export.png`);
fs.writeFileSync(`${OUT}/export.png`, Buffer.from(await png.arrayBuffer()));
fs.writeFileSync(
  `${OUT}/offset-run.json`,
  JSON.stringify({ job: receipt.id, zoom, viewport: "1708x2060", dpr: 1 }, null, 2),
);
console.log("zoom", zoom);
await browser.close();
