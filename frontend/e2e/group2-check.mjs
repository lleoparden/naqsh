// Group 2: layers list, rename, reorder, export menu, cover ellipse, shared colour.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8000";
const JOB = "d3dbface16b8";
const OUT = "L:/naqsh-review/group2";
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
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

fs.rmSync(`L:/naqsh/backend/.cache/jobs/${JOB}/document.json`, { force: true });
await page.goto(`${BASE}/?job=${JOB}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.screenshot({ path: `${OUT}/01-editor.png` });

// Layers: original + plate + three text layers.
const rows = await page.locator('[data-testid="layers-list"] li').count();
record("layers list has every layer", rows === 5, `rows: ${rows}`);

// Rename inline.
await page.getByLabel("Rename t1").click();
await page.waitForTimeout(250);
const renameInput = page.locator('[data-testid="layers-list"] input').first();
await renameInput.fill("Title banner");
await renameInput.press("Enter");
await page.waitForTimeout(1000);
const renamed = (await doc()).layers.find((layer) => layer.id === "t1")?.name;
record("inline rename persists", renamed === "Title banner", `name: ${renamed}`);
await page.screenshot({ path: `${OUT}/02-layers-renamed.png` });

// Export menu.
await page.getByRole("button", { name: "Export" }).click();
await page.waitForTimeout(200);
const items = await page.getByRole("menuitem").count();
const descriptions = await page.getByRole("menuitem").first().textContent();
record("export menu", items === 4 && Boolean(descriptions?.includes("Editable")), `${items} items; first: ${descriptions}`);
await page.screenshot({ path: `${OUT}/03-export-menu.png` });
await page.keyboard.press("Escape");

// Ellipse cover patch.
await page.locator('nav[aria-label="Tools"] button[aria-label="Cover patch"]').click();
await page.locator('nav[aria-label="Tools"] button[aria-label="Ellipse patch"]').click();
const canvasBox = await page.locator('[data-testid="canvas-svg"]').boundingBox();
await page.mouse.move(canvasBox.x + 100, canvasBox.y + 120);
await page.mouse.down();
await page.mouse.move(canvasBox.x + 220, canvasBox.y + 220, { steps: 8 });
await page.mouse.up();
await page.waitForTimeout(1200);
const covers = (await doc()).layers.filter((layer) => layer.kind === "cover");
record("ellipse cover patch", covers.length === 1 && covers[0].shape === "ellipse", `covers: ${covers.length}, shape: ${covers[0]?.shape}`);
await page.screenshot({ path: `${OUT}/04-cover-ellipse.png` });

// Shared colour control: hex input changes text colour.
await page.locator('[data-testid="layers-list"] li').filter({ hasText: "Title banner" }).first().locator("button").nth(2).click();
await page.waitForTimeout(300);
const hex = page.getByLabel("Colour hex").first();
await hex.fill("#ff0000");
await hex.press("Tab");
await page.waitForTimeout(900);
const colour = (await doc()).layers.find((layer) => layer.id === "t1")?.color;
record("hex colour applies", Array.isArray(colour) && colour[0] === 255 && colour[1] === 0, `colour: ${colour}`);

// Eyedropper changes the selected text colour.
await page.locator('nav[aria-label="Tools"] button[aria-label="Eyedropper"]').click();
await page.mouse.click(canvasBox.x + 60, canvasBox.y + 300);
await page.waitForTimeout(700);
const picked = (await doc()).layers.find((layer) => layer.id === "t1")?.color;
record("eyedropper applies", JSON.stringify(picked) !== JSON.stringify(colour), `colour: ${picked}`);
await page.screenshot({ path: `${OUT}/05-eyedropper.png` });

record("no console errors", errors.length === 0, errors.slice(0, 2).join(" | ") || "none");
fs.writeFileSync(`${OUT}/group2.json`, JSON.stringify({ results, consoleErrors: errors }, null, 2));
await browser.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
