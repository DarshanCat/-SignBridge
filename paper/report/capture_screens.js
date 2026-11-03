// Screenshots of every tab of the running production build (http://localhost:3110, API 8110) for the project report, and avatar frames across one sentence.
// A fake camera plays a head-masked copy of an INCLUDE video (see mask_video.py), so no face appears. Nothing is recorded or saved by the app.
// usage: node capture_screens.js <fake camera .y4m> <output folder>      (needs playwright-core and Chrome; run from any folder with NODE_PATH set)
const { chromium } = require("playwright-core");
const path = require("path");
const fs = require("fs");

const [y4m, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const URL = process.env.APP_URL || "http://localhost:3110";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const shotPath = (n) => path.join(outDir, n);

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", `--use-file-for-fake-video-capture=${y4m}`, "--autoplay-policy=no-user-gesture-required",
      "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, permissions: ["camera"] });
  const page = await ctx.newPage();
  let currentTab = "Conversation";
  const tab = async (label) => { currentTab = label; await page.getByRole("tab", { name: label, exact: true }).click(); await sleep(700); };
  // MediaPipe's start-up fails now and then (an empty data file is read); reloading the page and trying again is what a user would do
  const startCamera = async () => {
    for (let attempt = 1; attempt <= 4; attempt++) {
      await page.getByRole("button", { name: "Start camera" }).first().click();
      try {
        await page.waitForFunction(() => /Stop camera/.test(document.body.innerText), null, { timeout: 50000 });
        return;
      } catch (e) {
        await page.reload({ waitUntil: "load" });
        await sleep(4000);
        await page.getByRole("tab", { name: currentTab, exact: true }).click();
        await sleep(700);
      }
    }
    throw new Error("camera did not start after 4 attempts");
  };
  const stopCamera = async () => { const b = page.getByRole("button", { name: "Stop camera" }); if (await b.count()) await b.first().click(); await sleep(300); };
  const full = (name) => page.screenshot({ path: shotPath(name), fullPage: true });

  await page.goto(URL, { waitUntil: "load" });
  await sleep(6000);

  // 1. Conversation: a signed message and a typed message that the avatar signs
  await tab("Conversation");
  await startCamera();
  await page.waitForFunction(() => /Resting\.|Signing…/.test(document.body.innerText), null, { timeout: 25000 }).catch(() => {});
  await page.waitForFunction(() => /Body pose detected/.test(document.body.innerText), null, { timeout: 40000 }).catch(() => {});
  await sleep(14000);
  const send = page.getByRole("button", { name: /Send signed sentence/ });
  if (await send.isEnabled()) await send.click();
  await sleep(500);
  await page.locator("#chat-text").fill("I went to the hospital yesterday");
  await page.locator("button[type=submit]").first().click();
  await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => /^Pause/.test(b.innerText)), null, { timeout: 90000 }).catch(() => {});
  await sleep(1500);
  await full("tab_conversation.png");
  await stopCamera();

  // 2. Sign to English: landmark overlay and an isolated recognition
  await tab("Sign → English");
  await startCamera();
  await page.waitForFunction(() => /Model ready:/.test(document.body.innerText), null, { timeout: 25000 }).catch(() => {});
  await sleep(6000);
  let tries = 0;
  for (; tries < 10; tries++) {
    await page.getByRole("button", { name: /Recognize sign/ }).click();
    await sleep(2200);
    if (/as gloss HAT/.test(await page.evaluate(() => document.body.innerText))) break;
    await sleep(1500);
  }
  console.log("recognize presses until the answer was the shown sign (HAT):", tries + 1);
  await full("tab_sign_to_english.png");
  await stopCamera();

  // 3. English to Sign: gloss shown and the avatar in the middle of a sign
  await tab("English → Sign");
  await page.getByPlaceholder("e.g. Hello, what is your name?").fill("Hello, thank you");
  await page.locator("section[aria-label='English to sign'] button").first().click();
  await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => /^(Play|Pause)/.test(b.innerText) && !b.disabled), null, { timeout: 120000 });
  const play = page.getByRole("button", { name: /^(Play|Pause)/ }).first();
  if (/Play/.test(await play.innerText())) await play.click();
  await sleep(1300);
  await full("tab_english_to_sign.png");

  // 4. Record sign (guided session form; nothing is recorded)
  await tab("Record sign");
  await sleep(500);
  await startCamera();
  await sleep(4000);
  await full("tab_record_sign.png");
  await stopCamera();

  // 5. Landmark check
  await tab("Landmark check");
  await startCamera();
  await sleep(4000);
  await full("tab_landmark_check.png");
  await stopCamera();

  // avatar frames across one sentence
  await tab("English → Sign");
  await page.getByPlaceholder("e.g. Hello, what is your name?").fill("Hello. Thank you. Good morning. Doctor.");
  await page.locator("section[aria-label='English to sign'] button").first().click();
  await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => /^(Play|Pause)/.test(b.innerText) && !b.disabled), null, { timeout: 120000 });
  const canvas = page.locator("canvas:visible").last();
  const play2 = page.getByRole("button", { name: /^(Play|Pause)/ }).first();
  if (/Play/.test(await play2.innerText())) await play2.click();
  const t0 = Date.now();
  let i = 0;
  fs.mkdirSync(path.join(outDir, "avatar_frames"), { recursive: true });
  while (Date.now() - t0 < 12000) {
    await canvas.screenshot({ path: path.join(outDir, "avatar_frames", `f${String(i++).padStart(3, "0")}.png`) });
  }
  console.log("done", fs.readdirSync(outDir).join(", "), i, "avatar frames");
  await browser.close();
})().catch((e) => {
  console.log("FATAL", String(e.stack).split(String.fromCharCode(10)).filter((l) => /capture_screens|waitFor/.test(l)).slice(0, 4).join(" | "));
  process.exit(1);
});
