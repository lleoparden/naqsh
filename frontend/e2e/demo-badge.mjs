// No model calls: this script only uses document/layout/reset/cover/export endpoints.
// Demo-mode evidence: the badge on the result page and in the editor, with ?clean=1.
// Usage: node e2e/demo-badge.mjs  (backend must run with DEMO_MODE=1)
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = "http://localhost:4174";
const API = "http://127.0.0.1:8010";
const FIXTURE = "L:/naqsh/assets/generated/fixtures/01-comic-flat.png";
const OUT = "../docs/evidence/demo";

fs.mkdirSync(OUT, { recursive: true });
const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`);
};

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });

await page.goto(`${BASE}/?clean=1`, { waitUntil: "networkidle" });
await page.setInputFiles("input[type=file]", FIXTURE);
await page.getByText("Demo mode", { exact: false }).first().waitFor({ timeout: 60000 });
const badge = await page.getByText("replaying a recorded run", { exact: false }).first().textContent();
record("badge on result page", Boolean(badge), badge || "missing");
const cleanStatus = await page.getByText("API key configured", { exact: false }).count();
record("clean hides dev status", cleanStatus === 0, `matches: ${cleanStatus}`);
const progress = await page.getByText("Replaying recorded stages", { exact: false }).count();
record("stage replay visible", progress > 0, `sections: ${progress}`);
await page.screenshot({ path: `${OUT}/demo-badge-home.png` });

// The replay is paced by the recorded 48.3 s; capture the finished receipt too.
await page.getByText("Download", { exact: false }).first().waitFor({ timeout: 90000 });
const receipt = await page.getByText("Receipt", { exact: false }).count();
const totalRow = await page.getByText(`${(await (await fetch(`${API}/api/health`)).json()).status}`, { exact: false }).count();
record("receipt after replay", receipt > 0, `receipt sections: ${receipt}, health matches: ${totalRow}`);
await page.screenshot({ path: `${OUT}/demo-badge-home-done.png` });

// Editor badge: open the job the replay just produced.
const jobId = await page.evaluate(() => {
  const link = Array.from(document.querySelectorAll("a")).find((anchor) => anchor.textContent?.includes("Open editor"));
  return link ? new URL(link.href).searchParams.get("job") : null;
});
record("editor link", Boolean(jobId), jobId || "missing");
if (jobId) {
  await page.goto(`${BASE}/?job=${jobId}`, { waitUntil: "networkidle" });
  await page.getByText("Demo mode", { exact: false }).first().waitFor({ timeout: 20000 });
  record("badge in editor", true, `job ${jobId}`);
  await page.screenshot({ path: `${OUT}/demo-badge-editor.png` });
}

fs.writeFileSync(`${OUT}/demo-badge.json`, JSON.stringify({ results }, null, 2));
await browser.close();
const failed = results.filter((entry) => !entry.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
