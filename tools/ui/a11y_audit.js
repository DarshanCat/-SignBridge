// Accessibility audit of the running app: axe-core (WCAG 2.0/2.1 A and AA plus best practice) on every tab, in light and dark, on desktop and on a phone,
// and a check that the page never scrolls sideways. Needs playwright-core and axe-core (npm install in any folder, then NODE_PATH=<that folder>/node_modules),
// Chrome, and the app on http://localhost:3110 (production build recommended: npm run build; npm start -- -p 3110) with the API on 8110.
// usage: node a11y_audit.js          prints one line per tab and combination, and the offending elements if there are any
const { chromium } = require("playwright-core");
const fs = require("fs");
const axeSrc = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TABS = [["Conversation"], ["Sign → English"], ["English → Sign"], ["Record sign"], ["Landmark check"]];
(async () => {
  const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  let total = 0;
  for (const [scheme, w, h] of [["light", 1440, 1000], ["dark", 1440, 1000], ["light", 390, 844], ["dark", 390, 844]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
    const page = await ctx.newPage();
    await page.goto("http://localhost:3110", { waitUntil: "load" });
    await page.waitForFunction(() => /Backend connected/.test(document.body.innerText), null, { timeout: 120000 }).catch(() => {});
    await sleep(4000);
    for (const [label] of TABS) {
      await page.getByRole("tab", { name: label, exact: true }).click();
      await sleep(2500);
      await page.evaluate(axeSrc);
      const res = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"] }, resultTypes: ["violations"] });
        return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, sample: v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | "), help: v.help }));
      });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      console.log(`${scheme} ${w}px | ${label}: ${res.length} violation types, overflow ${overflow}px`);
      for (const v of res) { console.log("    ", v.impact, v.id, "x" + v.n, "-", v.help, "::", v.sample.slice(0, 120)); total += v.n; }
    }
    await ctx.close();
  }
  console.log("TOTAL nodes with violations:", total);
  await browser.close();
})();
