// Full-page screenshots of the app tabs (same requirements as a11y_audit.js). The English to Sign tab translates 'Hello doctor' and starts playing first.
// usage: node capture_tabs.js <outDir> <prefix> <scheme light|dark> <width> <height> [tabs comma list, e.g. conversation,english-to-sign]
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const [outDir, prefix, scheme, w, h, only] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const URL = process.env.APP_URL || "http://localhost:3110";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TABS = [
  ["conversation", "Conversation"],
  ["sign-to-english", "Sign → English"],
  ["english-to-sign", "English → Sign"],
  ["record-sign", "Record sign"],
  ["landmark-check", "Landmark check"],
];
(async () => {
  const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const ctx = await browser.newContext({ viewport: { width: +w, height: +h }, colorScheme: scheme, deviceScaleFactor: 1, hasTouch: +w < 500 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message.slice(0, 160)));
  await page.goto(URL, { waitUntil: "load" });
  await page.waitForFunction(() => /Backend connected/.test(document.body.innerText), null, { timeout: 120000 }).catch(() => errors.push("backend never connected"));
  for (const [id, label] of TABS) {
    if (only && !only.split(",").includes(id)) continue;
    await page.getByRole("tab", { name: label, exact: true }).click();
    await sleep(id === "conversation" || id === "english-to-sign" ? 6000 : 2500);
    if (id === "conversation" || id === "english-to-sign") await page.waitForFunction(() => /Avatar: (anime|Mixamo|built-in)/.test(document.body.innerText), null, { timeout: 150000 }).catch(() => errors.push("avatar never loaded"));
    if (id === "english-to-sign") {
      await page.getByPlaceholder("e.g. Hello, what is your name?").fill("Hello doctor");
      await page.getByRole("button", { name: "Translate" }).click();
      await page.waitForFunction(() => /Measured translate/.test(document.body.innerText), null, { timeout: 150000 }).catch(() => errors.push("translate never finished"));
      await page.waitForFunction(() => /[0-9]+ verified,/.test(document.body.innerText), null, { timeout: 150000 }).catch(() => errors.push("vocabulary never loaded"));
      await sleep(800);
      await page.getByRole("button", { name: "Play", exact: true }).click({ timeout: 100000 }).catch(() => errors.push("play not clickable"));
      await sleep(1100);
    }
    await page.screenshot({ path: path.join(outDir, `${prefix}_${id}.png`), fullPage: true });
  }
  console.log("errors:", JSON.stringify(errors.slice(0, 8)));
  await browser.close();
})();
