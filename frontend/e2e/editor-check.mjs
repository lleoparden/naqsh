// Real click-through of the editor with Playwright (chromium-core + installed Chrome).
// Usage: node e2e/editor-check.mjs
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const JOB = "6a8aa7a0829b";
const OUT = "../docs/evidence/phase-6";

const results = [];
function record(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
}

async function doc() {
  const response = await fetch(`${API}/api/jobs/${JOB}/document`);
  return response.json();
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
const notFound = [];
page.on("response", (response) => { if (response.status() === 404) notFound.push(response.url()); });
// Start from a clean document so box positions and cover count do not drift between runs.
const docPath = `L:/naqsh/backend/.cache/jobs/${JOB}/document.json`;
if (fs.existsSync(docPath)) fs.rmSync(docPath);
await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.screenshot({ path: `${OUT}/e2e-0-loaded.png` });

// 1. select from the layer list
const t1 = page.locator("aside button", { hasText: "t1" }).first();
await t1.click();
const panelTitle = await page.locator("aside .font-mono").first().textContent();
record("select from list", panelTitle?.trim() === "t1", `panel shows ${panelTitle}`);
await page.screenshot({ path: `${OUT}/e2e-1-selected.png` });

// 2. type RTL text and persist via PATCH
const textarea = page.locator("textarea[dir=rtl]");
const docNow = await doc();
const before = docNow.layers.find((layer) => layer.id === "t1").arabic[docNow.register];
const value = "اختبار التحرير";
await textarea.fill(value);
await textarea.press("Tab");
await page.waitForTimeout(900);
const docAfter = await doc();
record("type in textarea", docAfter.layers.find((layer) => layer.id === "t1").arabic[docAfter.register] === value, "document has the new Arabic");

// 3. reload persistence
await page.reload({ waitUntil: "networkidle" });
await page.waitForSelector("svg text");
const restored = await page.locator("textarea[dir=rtl]").inputValue();
record("reload persistence", restored === value, `textarea after reload: ${restored}`);

// 4. drag the selected box
await page.locator("aside button", { hasText: "t1" }).first().click();
const boxBefore = (await doc()).layers.find((layer) => layer.id === "t1").box;
const outline = page.locator('svg rect[stroke="#a6342c"]').first();
const rect = await outline.boundingBox();
await page.mouse.move(rect.x + rect.width / 2, rect.y + rect.height / 2);
await page.mouse.down();
await page.mouse.move(rect.x + rect.width / 2 + 40, rect.y + rect.height / 2 + 20, { steps: 8 });
await page.mouse.up();
await page.waitForTimeout(900);
const boxAfterDrag = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("drag box", boxAfterDrag[0] !== boxBefore[0], `${boxBefore} -> ${boxAfterDrag}`);
await page.screenshot({ path: `${OUT}/e2e-2-dragged.png` });

// 5. resize with the handle
const handle = page.locator('svg rect[fill="#a6342c"]').first();
const handleBox = await handle.boundingBox();
await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
await page.mouse.down();
await page.mouse.move(handleBox.x + handleBox.width / 2 + 30, handleBox.y + handleBox.height / 2 + 30, { steps: 6 });
await page.mouse.up();
await page.waitForTimeout(900);
const boxAfterResize = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("resize box", boxAfterResize[2] > boxAfterDrag[2], `${boxAfterDrag} -> ${boxAfterResize}`);

// 6. undo / redo
await page.keyboard.press("Control+z");
await page.waitForTimeout(900);
const afterUndo = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("undo", afterUndo[2] === boxAfterDrag[2], `width back to ${afterUndo[2]}`);
await page.keyboard.press("Control+y");
await page.waitForTimeout(900);
const afterRedo = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("redo", afterRedo[2] === boxAfterResize[2], `width ${afterRedo[2]}`);
await page.screenshot({ path: `${OUT}/e2e-3-redo.png` });

// 7. cover drag
const layersBefore = (await doc()).layers.length;
await page.getByRole("button", { name: "Cover patch" }).click();
const canvas = page.locator("svg").first();
const canvasBox = await canvas.boundingBox();
const coverResponse = page
  .waitForResponse((response) => response.url().includes("/cover") && response.request().method() === "POST", { timeout: 5000 })
  .catch(() => null);
await page.mouse.move(canvasBox.x + 40, canvasBox.y + canvasBox.height * 0.6);
await page.mouse.down();
await page.mouse.move(canvasBox.x + 160, canvasBox.y + canvasBox.height * 0.6 + 60, { steps: 8 });
await page.mouse.up();
const coverStatus = (await coverResponse)?.status() ?? "no request";
await page.waitForTimeout(1200);
const layersAfter = (await doc()).layers;
const covers = layersAfter.filter((layer) => layer.kind === "cover").length;
record("cover drag", layersAfter.length > layersBefore && covers >= 1, `layers ${layersBefore} -> ${layersAfter.length}, covers ${covers}, POST ${coverStatus}`);
await page.screenshot({ path: `${OUT}/e2e-4-cover.png` });

// 8. reload persistence of the cover
await page.reload({ waitUntil: "networkidle" });
await page.waitForSelector("svg text");
const coversAfterReload = (await doc()).layers.filter((layer) => layer.kind === "cover").length;
record("cover persists after reload", coversAfterReload === covers, `covers ${coversAfterReload}`);
await page.screenshot({ path: `${OUT}/e2e-5-reloaded.png` });

record("no console errors", errors.length === 0, `${errors.slice(0, 3).join(" | ") || "none"}${notFound.length ? `; 404: ${notFound.join(", ")}` : ""}`);
fs.writeFileSync(`${OUT}/e2e.json`, JSON.stringify({ job: JOB, results, consoleErrors: errors }, null, 2));
await browser.close();
const failed = results.filter((entry) => !entry.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
