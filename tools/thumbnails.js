// Screenshot every chart for the subtopic tiles: images/charts/<id>.png.
//
// Serves the built site, opens each chart page from charts/index.json and
// captures the plot alone at 900x600. Run after `quarto render`:
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
  for (const c of charts) {
    if (only.length && !only.includes(c.id)) continue;
    await page.goto(`http://localhost:${port}/charts/${c.id}.html`);
    await page.waitForSelector("#plot .main-svg");
    await page.waitForTimeout(500);
    // A tile is 3:2, so crop the plot to that shape.
    const box = await page.locator("#plot").boundingBox();
    const h = Math.min(box.height, Math.round(box.width / 1.5));
    await page.screenshot({ path: path.join(OUT, `${c.id}.png`), clip: { x: box.x, y: box.y + (box.height - h) / 2, width: box.width, height: h } });
    console.log("wrote", `images/charts/${c.id}.png`);
  }
  await browser.close();
  server.close();
})();
