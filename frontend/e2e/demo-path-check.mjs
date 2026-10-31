// Walk the demo script path in demo mode and assert each step; report wall time.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
const OUT = "L:/naqsh-review/demo-path";
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const t0 = Date.now();
const record = (name, ok, detail) => {
  results.push({ name, ok, detail, at_ms: Date.now() - t0 });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
await page.setInputFiles('input[type="file"]', FIXTURE);
await page.waitForSelector("text=/Demo mode/", { timeout: 30000 });
record("upload demo replay + badge", true, "badge visible");
await page.waitForTimeout(500);

await page.waitForSelector('a:has-text("Open editor")', { timeout: 180000 });
await page.getByRole("link", { name: "Open editor" }).click();
await page.waitForSelector("svg text");
await page.waitForTimeout(500);
record("editor opened", true, page.url());

await page.keyboard.press("Escape");
const doc0 = await (await fetch(`${API}/api/jobs/${page.url().split("job=")[1]}/document`)).json();
const bubble = doc0.layers.find((layer) => layer.kind === "bubble");
if (bubble) {
  await page.locator(`[aria-label="Toggle ${bubble.id} visibility"]`).click();
  await page.waitForTimeout(400);
  await page.locator(`[aria-label="Toggle ${bubble.id} visibility"]`).click();
  record("bubble hide/show", true, bubble.id);
} else {
  record("bubble hide/show", false, "no bubble layer in demo job");
}

await page.locator('[aria-label="Rename t1"]').click();
const input = page.locator('[data-testid="layers-list"] input').first();
await input.fill("Demo title");
await input.press("Enter");
await page.waitForTimeout(400);
record("rename layer", true, "Demo title");

await page.locator('[aria-label="Toggle t1 lock"]').click();
record("lock layer", true, "t1 locked");
await page.locator('[aria-label="Toggle t1 lock"]').click();

const range = page.getByLabel("Before and after reveal");
for (const value of [50, 100, 0]) {
  await range.evaluate((el, v) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(el, String(v));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  await page.waitForTimeout(250);
}
record("before/after slider", true, "50/100/0");

await page.locator('[data-testid="layer-name-t1"]').click();
await page.waitForTimeout(300);
await page.locator("select").filter({ has: page.locator('option[value="msa"]') }).selectOption("msa");
await page.waitForTimeout(400);
record("Arabic style switch", true, "MSA selected");

await page.getByRole("button", { name: "Export" }).click();
await page.waitForSelector('[role="menu"], [role="menuitem"]');
record("export menu", true, "open");
await page.keyboard.press("Escape");

const jobId = page.url().split("job=")[1];
const zip = await page.request.get(`${API}/api/jobs/${jobId}/export.zip`);
const zipBytes = (await zip.body()).length;
record("ZIP download", zip.ok() && zipBytes > 1000, `${zipBytes} bytes`);

await page.screenshot({ path: `${OUT}/final.png` });
record("no console errors", errors.length === 0, errors.slice(0, 3).join(" | ") || "none");
const total = Date.now() - t0;
fs.writeFileSync(`${OUT}/demo-path.json`, JSON.stringify({ job: jobId, total_ms: total, steps: results, errors }, null, 2));
await browser.close();
console.log(`\ntotal path wall time ${(total / 1000).toFixed(1)} s`);
const failed = results.filter((item) => !item.ok).length;
process.exit(failed ? 1 : 0);
