// Background layers: scenery + bubbles are separate, toggleable, and exported.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const JOB = "d3dbface16b8";
const OUT = "L:/naqsh-review/bg";

fs.mkdirSync(OUT, { recursive: true });
const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};
const doc = async () => (await fetch(`${API}/api/jobs/${JOB}/document`)).json();

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
const bad = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
page.on("response", (response) => { if (response.status() >= 500) bad.push(`${response.status()} ${response.url()}`); });

await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.keyboard.press("Escape");
await page.waitForTimeout(500);
await page.screenshot({ path: `${OUT}/01-layers.png` });

const list = (await page.locator('[data-testid="layers-list"]').textContent()) || "";
record("scenery layer shown", list.includes("Scenery"), list.slice(0, 100));
record("bubble layers shown", (list.match(/Bubble/g) || []).length >= 2, `count: ${(list.match(/Bubble/g) || []).length}`);

const before = (await doc()).layers.filter((layer) => layer.kind === "bubble").length;
record("bubbles in document", before >= 2, `${before} bubble layers`);

// Collapse the first bubble by its visible toggle.
await page.locator('[aria-label="Toggle bubble-t1 visibility"]').click();
await page.waitForTimeout(900);
const after = (await doc()).layers.find((layer) => layer.id === "bubble-t1");
record("bubble hidden persists", after.visible === false, `visible=${after.visible}`);
await page.screenshot({ path: `${OUT}/02-bubble-hidden.png` });

const svg = await (await fetch(`${API}/api/jobs/${JOB}/export.svg`)).text();
record("export has scenery group", svg.includes('data-name="Scenery"') && svg.includes("data:image/png;base64,"), "scenery image embedded");
record("export has bubbles group", svg.includes('id="bubbles"'), "bubbles group present");
record("hidden bubble omitted from export", !svg.includes('id="bubble-t1"'), "bubble-t1 not embedded");

// Restore.
await page.locator('[aria-label="Toggle bubble-t1 visibility"]').click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/03-bubble-restored.png` });

record("no console errors", errors.length === 0, `${errors.slice(0, 2).join(" | ") || "none"} ${bad.join(", ")}`);
fs.writeFileSync(`${OUT}/background.json`, JSON.stringify({ results, consoleErrors: errors }, null, 2));
await browser.close();
const failed = results.filter((item) => !item.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
