// Automated WCAG AA contrast check (axe-core) on the editor and home screens.
// No model calls. Usage: node e2e/contrast-check.mjs
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const OUT = "L:/naqsh-review/contrast";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const axePath = path.resolve("node_modules/axe-core/axe.min.js");

const results = [];
for (const [name, url] of [
  ["editor", `${BASE}/?job=d3dbface16b8`],
  ["home", `${BASE}/`],
]) {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  await page.addScriptTag({ path: axePath });
  const report = await page.evaluate(async () => {
    const result = await window.axe.run(document, { runOnly: ["color-contrast"] });
    return result.violations.flatMap((violation) =>
      violation.nodes.map((node) => ({
        id: violation.id,
        impact: violation.impact,
        target: node.target.join(" "),
        html: node.html.slice(0, 160),
        summary: node.failureSummary,
      })),
    );
  });
  results.push({ page: name, violations: report });
  console.log(`${name}: ${report.length} contrast violation node(s)`);
  for (const item of report.slice(0, 12)) {
    console.log(`  ${item.target} :: ${item.html}`);
  }
}

fs.writeFileSync(`${OUT}/axe.json`, JSON.stringify(results, null, 2));
await browser.close();
const total = results.reduce((sum, item) => sum + item.violations.length, 0);
console.log(`total: ${total}`);
process.exit(total === 0 ? 0 : 1);
