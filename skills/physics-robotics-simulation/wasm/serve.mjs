#!/usr/bin/env node
// Serve the browser preview on this machine only.
//
// USAGE: node serve.mjs BUNDLE_DIR [--port 8765] [--isolate]
//
// Binds 127.0.0.1, never 0.0.0.0. Serves this folder (the page, the worker, node_modules) and
// BUNDLE_DIR under /bundle/. --isolate adds the two headers the multi-threaded build needs
// (Cross-Origin-Opener-Policy: same-origin, Cross-Origin-Embedder-Policy: require-corp); without
// them the page runs the single-threaded build, which is the default.
import { createServer } from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const bundle = args[0] && !args[0].startsWith('--') ? await realpath(resolve(args[0])) : null;
const port = Number(args[args.indexOf('--port') + 1]) || 8765;
const isolate = args.includes('--isolate');
if (!bundle) {
  console.error('usage: node serve.mjs BUNDLE_DIR [--port 8765] [--isolate]');
  process.exit(1);
}
const here = await realpath(fileURLToPath(new URL('.', import.meta.url)));
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.wasm': 'application/wasm', '.json': 'application/json', '.xml': 'text/xml', '.obj': 'text/plain',
  '.png': 'image/png', '.stl': 'application/octet-stream',
};

// A path is served only when the file it names, links followed, lies inside root.
async function inside(root, rel) {
  const full = await realpath(normalize(join(root, rel))).catch(() => null);
  return full && (full === root || full.startsWith(root + sep)) ? full : null;
}

createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = path.startsWith('/bundle/') ? await inside(bundle, path.slice(8))
    : await inside(here, path === '/' ? 'web/index.html' : path.slice(1));
  const headers = { 'Cache-Control': 'no-store' };
  if (isolate) {
    headers['Cross-Origin-Opener-Policy'] = 'same-origin';
    headers['Cross-Origin-Embedder-Policy'] = 'require-corp';
  }
  try {
    if (!file || !(await stat(file)).isFile()) throw new Error('not found');
    const body = await readFile(file);
    res.writeHead(200, { ...headers, 'Content-Type': types[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404, headers);
    res.end('not found');
  }
}).listen(port, '127.0.0.1', () => {
  console.log(`preview on http://127.0.0.1:${port}/ (${isolate ? 'cross-origin isolated' : 'single-threaded'})`);
});
