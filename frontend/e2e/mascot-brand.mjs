// Brand exports: favicon source + 32 px PNG, README header, X avatar, X banner.
import { chromium } from "playwright-core";
import fs from "node:fs";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SVG = fs.readFileSync("L:/naqsh/assets/mascot/naqsh.svg", "utf8");
const OUT = "L:/naqsh-review/mascot-assets/brand";
fs.mkdirSync(OUT, { recursive: true });

const font = (name) => `data:font/ttf;base64,${fs.readFileSync(`L:/naqsh/assets/fonts/${name}`).toString("base64")}`;
const browser = await chromium.launch({ executablePath: CHROME, headless: true });

async function shot(width, height, html, name) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(html);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${name}`, omitBackground: false });
  await page.close();
}

const header = `<!doctype html><style>
@font-face{font-family:Inter;src:url('${font("Inter-Variable.ttf")}')}
@font-face{font-family:Plex;src:url('${font("IBMPlexSansArabic-Regular.ttf")}')}
html,body{margin:0;width:1500px;height:500px;background:#f3eee8;overflow:hidden}
.wrap{display:flex;align-items:center;gap:54px;padding:0 72px;height:100%;box-sizing:border-box}
.mascot{width:300px;height:300px}
h1{font:600 112px/1 Inter;color:#1b1b1f;margin:0;letter-spacing:-0.03em}
.ar{font:400 82px/1 Plex;color:#a94a4a;margin-top:8px}
p{font:400 24px/1.3 Inter;color:#5b5550;margin:18px 0 0}
</style><div class="wrap"><div class="mascot">${SVG}</div><div><h1>Naqsh</h1><div class="ar">نقش</div><p>Arabic-first image localizer</p></div></div>`;

const avatar = `<!doctype html><style>html,body{margin:0;width:400px;height:400px;background:#f3eee8;display:grid;place-items:center}svg{width:320px;height:320px}</style>${SVG}`;

const banner = `<!doctype html><style>
@font-face{font-family:Inter;src:url('${font("Inter-Variable.ttf")}')}
@font-face{font-family:Plex;src:url('${font("IBMPlexSansArabic-Regular.ttf")}')}
html,body{margin:0;width:1500px;height:500px;background:#1b1b1f;overflow:hidden}
.wrap{display:flex;align-items:center;gap:60px;height:100%;padding:0 80px;box-sizing:border-box}
.mascot{width:300px;height:300px}
h1{font:600 120px/1 Inter;color:#f3eee8;margin:0;letter-spacing:-0.03em}
.ar{font:400 86px/1 Plex;color:#e07c7b;margin-top:6px}
p{font:400 24px/1.3 Inter;color:#c6bfb7;margin:20px 0 0}
</style><div class="wrap"><div class="mascot">${SVG}</div><div><h1>Naqsh</h1><div class="ar">نقش</div><p>Arabic-first image localizer</p></div></div>`;

await shot(1500, 500, header, "readme-header-1500x500.png");
await shot(400, 400, avatar, "x-avatar-400.png");
await shot(1500, 500, banner, "x-banner-1500x500.png");
await browser.close();
console.log("brand exports written");
