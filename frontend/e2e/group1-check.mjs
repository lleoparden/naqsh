// Group 1 checks: font re-typeset, live size, reset to AI, original hides overlays,
// before/after slider with keyboard and pointer, digits on the menu.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:5176";
const API = "http://127.0.0.1:8000";
const COMIC = "d3dbface16b8";
const MENU = "e13f9585b24f";
const OUT = "L:/naqsh-review/group1";
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};

const docOf = async (id) => (await fetch(`${API}/api/jobs/${id}/document`)).json();

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

// Clean start for the comic document.
const docPath = `L:/naqsh/backend/.cache/jobs/${COMIC}/document.json`;
if (fs.existsSync(docPath)) fs.rmSync(docPath);
await page.goto(`${BASE}/?job=${COMIC}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.locator("aside button", { hasText: "t1" }).first().click();
await page.screenshot({ path: `${OUT}/01-selected.png` });

// 1. font change actually re-typesets
const beforeFont = (await docOf(COMIC)).layers.find((l) => l.id === "t1").font_family;
await page.locator('[data-testid="font-select"]').selectOption("amiri");
await page.waitForTimeout(1200);
const afterFont = (await docOf(COMIC)).layers.find((l) => l.id === "t1");
record("font re-typesets", afterFont.font_family === "amiri" && afterFont.font_size > 0,
  `${beforeFont} -> ${afterFont.font_family}, size ${afterFont.font_size}`);
await page.screenshot({ path: `${OUT}/02-font-amiri.png` });

// 2. live size via slider
await page.locator('[data-testid="size-slider"]').evaluate((el) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setter.call(el, "60");
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(900);
const sized = (await docOf(COMIC)).layers.find((l) => l.id === "t1");
record("size updates live", sized.font_size === 60, `document font_size ${sized.font_size}`);

// 3. reset to AI result restores the first generation
const aiText = (await docOf(COMIC)).layers.find((l) => l.id === "t1").original.arabic.egyptian;
await page.locator("textarea[aria-label='Arabic text']").fill("نص مؤقت للاختبار");
await page.locator("textarea[aria-label='Arabic text']").press("Tab");
await page.waitForTimeout(800);
await page.getByRole("button", { name: "Reset to AI result" }).click();
await page.waitForTimeout(1200);
const resetLayer = (await docOf(COMIC)).layers.find((l) => l.id === "t1");
record("reset to AI result", resetLayer.arabic.egyptian === aiText, "original text restored");
await page.screenshot({ path: `${OUT}/03-reset.png` });

// 4. original hides overlays
await page.getByRole("button", { name: "Original" }).click();
await page.waitForTimeout(400);
const textCount = await page.locator("svg text").count();
record("original hides overlays", textCount === 0, `text elements on canvas: ${textCount}`);
await page.screenshot({ path: `${OUT}/04-original.png` });
await page.getByRole("button", { name: "Original" }).click();
await page.waitForTimeout(300);

// 5. before/after slider keyboard + pointer
const range = page.getByLabel("Before and after reveal");
await range.focus();
await page.keyboard.press("ArrowLeft");
await page.keyboard.press("ArrowLeft");
const keyboardValue = Number(await range.inputValue());
record("slider keyboard", keyboardValue < 100, `value after two ArrowLeft: ${keyboardValue}`);

const divider = page.locator("svg line[stroke='#5B6CFF']").first();
const box = await divider.boundingBox();
if (box) {
  await page.mouse.move(box.x + box.width / 2, box.y + Math.min(200, box.height / 2));
  await page.mouse.down();
  await page.mouse.move(box.x - 120, box.y + Math.min(200, box.height / 2), { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(300);
}
const pointerValue = Number(await range.inputValue());
record("slider pointer drag", pointerValue < keyboardValue, `value after drag: ${pointerValue}`);
await page.screenshot({ path: `${OUT}/05-slider.png` });

// 6. digits on the menu: price layer switches to Arabic-Indic
await page.goto(`${BASE}/?job=${MENU}`, { waitUntil: "networkidle" });
await page.waitForSelector("svg text");
await page.evaluate(() => {
  const entries = Array.from(document.querySelectorAll("aside li button"));
  const price = entries.find((el) => el.textContent?.includes("price"));
  if (price) price.click();
});
await page.waitForTimeout(400);
await page.locator('[data-testid="numerals-select"]').selectOption("arabic-indic");
await page.waitForTimeout(1200);
const menuDoc = await docOf(MENU);
const lines = menuDoc.layers.flatMap((layer) => (layer.lines || []).map((line) => line.text));
const digitLine = lines.find((text) => /[٠-٩]/.test(text)) || "";
record("digits switch on the page", /[٠-٩]/.test(digitLine), `line: ${digitLine || lines[0] || "none"}`);
await page.screenshot({ path: `${OUT}/06-digits.png` });

record("no console errors", errors.length === 0, errors.slice(0, 2).join(" | ") || "none");
fs.writeFileSync(`${OUT}/group1.json`, JSON.stringify({ results, consoleErrors: errors }, null, 2));
await browser.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
