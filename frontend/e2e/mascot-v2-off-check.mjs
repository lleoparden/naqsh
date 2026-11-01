import { chromium } from "playwright-core";
const browser = await chromium.launch({ executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://localhost:4174/?clean=1&mascot=off", { waitUntil: "networkidle" });
console.log("mascot with ?mascot=off:", await page.locator(".mascot").count());
await browser.close();
