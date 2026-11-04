// Freeze check in the fresh clone: mascot states, off switches, overlap geometry, cache screenshots.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
const OUT = "L:/naqsh-review/freeze";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const report = { consoleErrors: [], mascotCounts: {}, overlap: [], states: {} };

page.on("console", (message) => { if (message.type() === "error") report.consoleErrors.push(message.text()); });

await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
report.mascotCounts.home = await page.locator(".mascot").count();
await page.screenshot({ path: `${OUT}/mascot-idle-1920.png` });
await page.hover(".mascot");
await page.waitForTimeout(300);
await page.screenshot({ path: `${OUT}/mascot-wave-1920.png` });

// empty state: editor with no selected layer (Escape deselects)
await page.goto(`${BASE}/?job=demo-7b45e1cb`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text", { timeout: 20000 });
await page.keyboard.press("Escape");
await page.waitForSelector("text=No region selected", { timeout: 10000 });
report.mascotCounts.empty = await page.locator(".mascot").count();
await page.screenshot({ path: `${OUT}/mascot-empty-1920.png` });

// loading state
await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
await page.route("**/api/localize", async (route) => {
  await new Promise((resolve) => setTimeout(resolve, 2500));
  await route.continue();
});
await page.setInputFiles('input[type="file"]', FIXTURE);
await page.waitForSelector("text=Localizing your page", { timeout: 10000 });
report.mascotCounts.loading = await page.locator(".mascot").count();
await page.screenshot({ path: `${OUT}/mascot-loading-1920.png` });

// success state after replay
await page.waitForSelector("text=Page localized", { timeout: 120000 });
await page.waitForSelector("text=Replaying recorded stages at their real pace", { state: "detached", timeout: 180000 });
await page.waitForTimeout(300);
report.mascotCounts.success = await page.locator(".mascot").count();
await page.screenshot({ path: `${OUT}/mascot-success-1920.png` });

// error state
await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
await page.route("**/api/localize", (route) =>
  route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "test failure" }) }),
);
await page.setInputFiles('input[type="file"]', FIXTURE);
await page.waitForSelector("text=Something went wrong", { timeout: 10000 });
report.mascotCounts.error = await page.locator(".mascot").count();
await page.screenshot({ path: `${OUT}/mascot-error-1920.png` });

// off by URL
await page.goto(`${BASE}/?clean=1&mascot=off`, { waitUntil: "networkidle" });
report.mascotCounts.offUrl = await page.locator(".mascot").count();

// overlap geometry: every mascot box vs canvas SVGs and visible receipt numbers
await page.goto(`${BASE}/?job=demo-1748595d`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text", { timeout: 20000 });
report.overlap = await page.evaluate(() => {
  const boxes = [...document.querySelectorAll(".mascot")].map((element) => {
    const rect = element.getBoundingClientRect();
    return { kind: "mascot", x: rect.x, y: rect.y, w: rect.width, h: rect.height };
  });
  const targets = [...document.querySelectorAll("svg")].filter((svg) => !svg.closest(".mascot")).map((svg) => {
    const rect = svg.getBoundingClientRect();
    return { kind: "canvas-svg", x: rect.x, y: rect.y, w: rect.width, h: rect.height };
  });
  const overlap = [];
  for (const a of boxes) {
    for (const b of targets) {
      const intersects = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
      if (intersects) overlap.push({ mascot: a, target: b });
    }
  }
  return overlap;
});
await page.screenshot({ path: `${OUT}/editor-1920.png` });

// cache screenshots via each demo job page
for (const [name, id] of [["phase1-baker", "demo-7b45e1cb"], ["comic-v4", "demo-1748595d"], ["zion", "demo-388acc42"]]) {
  await page.goto(`${BASE}/?job=${id}`, { waitUntil: "networkidle" });
  await page.waitForSelector("svg text", { timeout: 20000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/cache-${name}-1920.png` });
  report.states[name] = true;
}

fs.writeFileSync(`${OUT}/freeze-check.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
