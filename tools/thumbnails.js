// Screenshot every chart, for the subtopic tiles and for link previews.
//
// Serves the built site and opens each chart page from charts/index.json:
//   images/charts/<id>.png   the plot alone at 900x600, for subtopic tiles
//   images/social/<id>.png   the chart with its title at 1200x630, the preview
//                            image social media shows when the chart is shared
//   images/social/site.png   the preview image for the rest of the site
// Run after `quarto render`:
//   npm install playwright && npx playwright install chromium   (once)
//   node tools/thumbnails.js            # every chart
//   node tools/thumbnails.js population-total housing-completions
const { chromium } = require("playwright");
const fs = require("fs");
const http = require("http");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SITE = path.join(ROOT, "_site");
const OUT = path.join(ROOT, "images", "charts");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".csv": "text/csv", ".geojson": "application/json" };

(async () => {
  const charts = JSON.parse(fs.readFileSync(path.join(ROOT, "charts", "index.json"), "utf8"));
  const only = process.argv.slice(2);
  const server = http.createServer((req, res) => {
    const file = path.join(SITE, decodeURIComponent(req.url.split("?")[0]));
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  }).listen(0);
  const port = server.address().port;
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 900 }, deviceScaleFactor: 1 });
  const card = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  const SOCIAL = path.join(ROOT, "images", "social");
  fs.mkdirSync(SOCIAL, { recursive: true });
  for (const c of charts) {
    if (only.length && !only.includes(c.id)) continue;
    await card.goto(`http://localhost:${port}/charts/${c.id}.html?card`);
    await card.waitForSelector("#plot .main-svg");
    await card.waitForTimeout(500);
    await card.screenshot({ path: path.join(SOCIAL, `${c.id}.png`) });
    console.log("wrote", `images/social/${c.id}.png`);
    if (c.listed === false) continue;   // county charts have no tile
    await page.goto(`http://localhost:${port}/charts/${c.id}.html`);
    await page.waitForSelector("#plot .main-svg");
    await page.waitForTimeout(500);
    // A tile is 3:2, so crop the plot to that shape.
    const box = await page.locator("#plot").boundingBox();
    const h = Math.min(box.height, Math.round(box.width / 1.5));
    await page.screenshot({ path: path.join(OUT, `${c.id}.png`), clip: { x: box.x, y: box.y + (box.height - h) / 2, width: box.width, height: h } });
    console.log("wrote", `images/charts/${c.id}.png`);
  }
  if (!only.length) {
    await card.setContent(`<!doctype html><html><body style="margin:0;width:1200px;height:630px;display:flex;
      flex-direction:column;justify-content:center;padding:0 96px;box-sizing:border-box;background:#fff;
      font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;border-top:16px solid #2a78d6">
      <div style="font-size:84px;font-weight:700;color:#0b0b0b;line-height:1.05">Ireland by Numbers</div>
      <div style="font-size:38px;color:#52514e;margin-top:28px;line-height:1.3">Official Irish statistics in clear, interactive charts and maps</div>
      <div style="font-size:28px;color:#8a8984;margin-top:56px">irelandbynumbers.ie</div></body></html>`);
    await card.screenshot({ path: path.join(SOCIAL, "site.png") });
    console.log("wrote images/social/site.png");
  }
  await browser.close();
  server.close();
})();
