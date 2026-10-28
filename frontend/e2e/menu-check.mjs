// Menu-job click-through: select, edit text, drag, undo, reload persistence.
// Usage: node e2e/menu-check.mjs
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const JOB = "e13f9585b24f";
const OUT = "../docs/evidence/demo";

const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};

const doc = async () => (await fetch(`${API}/api/jobs/${JOB}/document`)).json();

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
fs.mkdirSync(OUT, { recursive: true });

const docPath = `L:/naqsh/backend/.cache/jobs/${JOB}/document.json`;
if (fs.existsSync(docPath)) fs.rmSync(docPath);
await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.screenshot({ path: `${OUT}/menu-editor-loaded.png` });

// 1. select
await page.locator("aside button", { hasText: "t1" }).first().click();
const selected = (await page.locator("aside .font-mono").first().textContent())?.trim();
record("menu select", selected === "t1", `panel shows ${selected}`);

// 2. edit text and persist
const textarea = page.locator("textarea[dir=rtl]");
const value = "قائمة الاختبار";
await textarea.fill(value);
await textarea.press("Tab");
await page.waitForTimeout(900);
const docAfterEdit = await doc();
record(
  "menu edit text",
  docAfterEdit.layers.find((layer) => layer.id === "t1").arabic[docAfterEdit.register] === value,
  "document has the new Arabic",
);

// 3. drag
const before = (await doc()).layers.find((layer) => layer.id === "t1").box;
const outline = page.locator('svg rect[stroke="#a6342c"]').first();
const rect = await outline.boundingBox();
await page.mouse.move(rect.x + rect.width / 2, rect.y + rect.height / 2);
await page.mouse.down();
await page.mouse.move(rect.x + rect.width / 2 + 40, rect.y + rect.height / 2 + 20, { steps: 8 });
await page.mouse.up();
await page.waitForTimeout(900);
const afterDrag = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("menu drag", afterDrag[0] !== before[0], `${before} -> ${afterDrag}`);
await page.screenshot({ path: `${OUT}/menu-editor-dragged.png` });

// 4. undo
await page.keyboard.press("Control+z");
await page.waitForTimeout(900);
const afterUndo = (await doc()).layers.find((layer) => layer.id === "t1").box;
record("menu undo", afterUndo[0] === before[0], `x ${afterDrag[0]} -> ${afterUndo[0]}`);

// 5. reload persistence
await page.reload({ waitUntil: "networkidle" });
await page.waitForSelector("svg text");
const restored = await page.locator("textarea[dir=rtl]").inputValue();
record("menu reload persistence", restored === value, `textarea after reload: ${restored}`);
await page.screenshot({ path: `${OUT}/menu-editor-reloaded.png` });

record("menu no console errors", errors.length === 0, errors.slice(0, 2).join(" | ") || "none");
fs.writeFileSync(`${OUT}/menu-e2e.json`, JSON.stringify({ job: JOB, results, consoleErrors: errors }, null, 2));
await browser.close();
const failed = results.filter((entry) => !entry.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
