// Layer panel controls in a real browser: drag reorder, lock guard, show/hide, rename.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const OUT = "L:/naqsh-review/layers";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};

const upload = await fetch(`${API}/api/localize`, {
  method: "POST",
  body: (() => {
    const data = new FormData();
    data.append("image", new Blob([fs.readFileSync(FIXTURE)], { type: "image/png" }), "comic.png");
    data.append("register", "egyptian");
    return data;
  })(),
});
const receipt = await upload.json();
if (!receipt.id) throw new Error(`upload failed: ${JSON.stringify(receipt).slice(0, 300)}`);
record("demo replay uploaded", Boolean(receipt.demo), `job ${receipt.id} demo=${receipt.demo}`);

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
await page.goto(`${BASE}/?job=${receipt.id}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.keyboard.press("Escape");
await page.waitForTimeout(500);

const doc = async () => (await fetch(`${API}/api/jobs/${receipt.id}/document`)).json();
const row = (id) => page.locator('[data-testid="layers-list"] li').filter({ has: page.locator(`[aria-label="Toggle ${id} visibility"]`) });
const drag = async (fromId, toId) => {
  await row(fromId).dragTo(row(toId));
  await page.waitForTimeout(600);
};

// Drag reorder: t2 above t1.
let before = await doc();
const zBefore = Object.fromEntries(before.layers.map((layer) => [layer.id, layer.z]));
await drag("t2", "t1");
let after = await doc();
const reordered = after.layers.find((layer) => layer.id === "t2").z === zBefore.t1
  && after.layers.find((layer) => layer.id === "t1").z === zBefore.t2;
record("drag reorder swaps z", reordered, `t1 ${zBefore.t1}->${after.layers.find((l) => l.id === "t1").z}, t2 ${zBefore.t2}->${after.layers.find((l) => l.id === "t2").z}`);
await page.screenshot({ path: `${OUT}/01-reordered.png` });

// Lock guard: lock t1, try to drag it, z must not change.
await page.locator('[aria-label="Toggle t1 lock"]').click();
await page.waitForTimeout(300);
const zLocked = (await doc()).layers.find((layer) => layer.id === "t1").z;
await drag("t1", "t3");
const zAfterLocked = (await doc()).layers.find((layer) => layer.id === "t1").z;
record("locked layer cannot be reordered", zLocked === zAfterLocked, `z ${zLocked} -> ${zAfterLocked}`);
await page.locator('[aria-label="Toggle t1 lock"]').click();
await page.waitForTimeout(300);

// Show/hide a bubble layer and persist it.
const bubble = (await doc()).layers.find((layer) => layer.kind === "bubble");
await page.locator(`[aria-label="Toggle ${bubble.id} visibility"]`).click();
await page.waitForTimeout(700);
const hidden = (await doc()).layers.find((layer) => layer.id === bubble.id).visible === false;
record("hide persists", hidden, `${bubble.id} visible=false`);
await page.screenshot({ path: `${OUT}/02-bubble-hidden.png` });
await page.locator(`[aria-label="Toggle ${bubble.id} visibility"]`).click();
await page.waitForTimeout(700);
const restored = (await doc()).layers.find((layer) => layer.id === bubble.id).visible === true;
record("show restores", restored, `${bubble.id} visible=true`);

// Rename t1.
await page.locator('[aria-label="Rename t1"]').click();
const input = page.locator('[data-testid="layers-list"] input').first();
await input.fill("Scene title");
await input.press("Enter");
await page.waitForTimeout(700);
const renamed = (await doc()).layers.find((layer) => layer.id === "t1").name === "Scene title";
record("inline rename persists", renamed, `name=${(await doc()).layers.find((layer) => layer.id === "t1").name}`);
await page.screenshot({ path: `${OUT}/03-renamed.png` });

record("no console errors", errors.length === 0, errors.slice(0, 2).join(" | ") || "none");
fs.writeFileSync(`${OUT}/layers.json`, JSON.stringify({ job: receipt.id, results, errors }, null, 2));
await browser.close();
const failed = results.filter((item) => !item.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
