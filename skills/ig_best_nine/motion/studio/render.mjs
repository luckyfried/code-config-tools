// Renders the best-nine film's jobs with one bundle and one browser, from this folder's composition, which is built on
// the kit's motion system (../system) and resolves every package from this kit's own node_modules.
//
// node render.mjs JOBS.json
// A video job may carry `frameRange` [first, last] to render that part of its composition alone.
import fs from 'node:fs';
import {createRequire} from 'node:module';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const system = path.resolve(here, '..');
const modules = path.join(system, 'node_modules');
const req = createRequire(path.join(system, 'package.json'));
const {bundle} = await import(pathToFileURL(req.resolve('@remotion/bundler')).href);
const {ensureBrowser, openBrowser, renderMedia, renderStill, selectComposition} = await import(pathToFileURL(req.resolve('@remotion/renderer')).href);

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const started = Date.now();
const findings = [];
const timings = [];

const onBrowserLog = (job) => (log) => {
  const text = String(log.text ?? '');
  if (/^(SAFE_BREACH|FONT_ERROR|UNKNOWN_KIND|IMAGE_ERROR)/.test(text)) findings.push({job: job.out, text});
};

await ensureBrowser();
// The bundle carries a copy of the public folder, so it is removed when the run ends.
const bundleDir = path.join(spec.bundleDir ?? path.join(os.tmpdir(), 'nine-bundle'), String(process.pid));
process.on('exit', () => fs.rmSync(bundleDir, {recursive: true, force: true}));
const serveUrl = await bundle({
  entryPoint: path.join(here, 'index.ts'),
  webpackOverride: (config) => ({
    ...config,
    resolve: {
      ...config.resolve,
      modules: [modules, 'node_modules'],
      alias: {...(config.resolve?.alias ?? {}), react: path.join(modules, 'react'), 'react-dom': path.join(modules, 'react-dom'), remotion: path.join(modules, 'remotion')},
    },
  }),
  publicDir: spec.publicDir,
  outDir: bundleDir,
});
const bundled = Date.now();
// With the NVIDIA device present, Chrome rasterizes on the card through ANGLE on Vulkan and NVENC encodes; without it, both stay on the CPU.
const gpu = fs.existsSync('/dev/nvidia0');
const gl = spec.gl ?? (gpu ? 'vulkan' : 'swangle');
const browser = await openBrowser('chrome', {chromiumOptions: {gl}});
const concurrency = spec.concurrency ?? (gpu ? 8 : Math.max(1, Math.min(16, Math.floor(os.cpus().length / 2))));
// NVENC takes no crf through Remotion: constant quality 18 with the bitrate ceiling lifted matches x264 crf 18.
const nvenc = ({type, args}) => (type === 'pre-stitcher'
  ? [...args.slice(0, -1), '-preset', 'p5', '-tune', 'hq', '-profile:v', 'high', '-rc', 'vbr', '-cq', '14', '-b:v', '0', '-maxrate', '80M', '-bufsize', '160M', args.at(-1)]
  : args);

let failed = 0;
let retries = 0;
// A transient browser fetch failure (an interface change on the host, a dropped proxy request) costs one job
// attempt, never the run: each job gets three attempts.
const runJob = async (job, t0) => {
  const composition = await selectComposition({serveUrl, id: job.composition, inputProps: job.props, puppeteerInstance: browser});
  if (job.type === 'video') {
    let last = -1;
    await renderMedia({
      serveUrl, composition, inputProps: job.props, puppeteerInstance: browser, outputLocation: job.out,
      codec: 'h264', pixelFormat: 'yuv420p', muted: true, scale: job.scale ?? 1, ...(job.frameRange ? {frameRange: job.frameRange} : {}),
      ...(gpu ? {hardwareAcceleration: 'required', ffmpegOverride: nvenc} : {crf: job.crf ?? 18, x264Preset: job.preset ?? 'medium'}),
      concurrency, onBrowserLog: onBrowserLog(job), chromiumOptions: {gl},
      onProgress: ({progress}) => {
        const p = Math.floor(progress * 10);
        if (p !== last) {
          last = p;
          process.stderr.write(`render ${path.basename(job.out)} ${p * 10}% (${((Date.now() - t0) / 1000).toFixed(0)} s)\n`);
        }
      },
    });
  } else {
    await renderStill({
      serveUrl, composition, inputProps: job.props, puppeteerInstance: browser, output: job.out,
      frame: Math.min(job.frame ?? 0, composition.durationInFrames - 1), scale: job.scale ?? 1, imageFormat: 'png',
      onBrowserLog: onBrowserLog(job),
    });
  }
};
for (const job of spec.jobs) {
  const t0 = Date.now();
  fs.mkdirSync(path.dirname(job.out), {recursive: true});
  let error = null;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      await runJob(job, t0);
      error = null;
      break;
    } catch (e) {
      error = e;
      if (attempt < 3) {
        retries++;
        process.stderr.write(`retrying ${path.basename(job.out)} (attempt ${attempt + 1} of 3): ${String(e?.message ?? e).slice(0, 200)}\n`);
      }
    }
  }
  if (error) {
    failed++;
    findings.push({job: job.out, text: `RENDER_ERROR ${String(error?.stack ?? error).slice(0, 1500)}`});
    process.stderr.write(`failed ${job.out}: ${String(error?.message ?? error)}\n`);
  } else {
    timings.push({out: job.out, seconds: (Date.now() - t0) / 1000});
  }
}
await browser.close({silent: true});
const report = {bundle_seconds: (bundled - started) / 1000, seconds: (Date.now() - started) / 1000, jobs: spec.jobs.length, failed, retries, findings, timings};
if (spec.report) fs.writeFileSync(spec.report, JSON.stringify(report, null, 2));
process.stderr.write(`rendered ${spec.jobs.length - failed} of ${spec.jobs.length} jobs in ${report.seconds.toFixed(1)} s\n`);
process.exit(failed ? 1 : 0);
