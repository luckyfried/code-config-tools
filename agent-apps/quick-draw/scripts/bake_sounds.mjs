// Renders every recipe in site/audio/synth.js offline in headless Chromium and writes site/audio/<name>.wav.
// Only needed after a recipe changes; run.py copies the WAV files as they are. Needs Node and Playwright:
//   node scripts/bake_sounds.mjs
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const SITE = fileURLToPath(new URL("../site/", import.meta.url));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };

const server = createServer(async (req, res) => {
  const path = normalize(join(SITE, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!path.startsWith(SITE)) return res.writeHead(403).end();
  try {
    const body = req.url === "/" ? "<!doctype html><title>bake</title>" : await readFile(path);
    res.writeHead(200, { "content-type": TYPES[extname(path)] || "text/html" }).end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const url = `http://127.0.0.1:${server.address().port}/`;

const { chromium } = await import(process.env.PLAYWRIGHT_ENTRY || "playwright");
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(url);
const files = await page.evaluate(async () => {
  const synth = await import("./audio/synth.js");
  const out = {};
  for (const name of synth.SOUND_NAMES) {
    const bytes = new Uint8Array(synth.toWav(await synth.renderSound(name)));
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    out[name] = btoa(bin);
  }
  return out;
});
for (const [name, b64] of Object.entries(files)) {
  const bytes = Buffer.from(b64, "base64");
  await writeFile(join(SITE, "audio", `${name}.wav`), bytes);
  console.log(`audio/${name}.wav ${bytes.length} bytes`);
}
await browser.close();
server.close();
