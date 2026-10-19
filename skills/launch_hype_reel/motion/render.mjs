// Renders a list of jobs with one bundle and one browser: the film, the cards, the style-sheet frames.
//
// node render.mjs JOBS.json
//
// JOBS.json: {"publicDir": "/abs/build", "report": "/abs/build/render-report.json",
//             "jobs": [{"type": "video", "composition": "Film", "props": {...}, "out": "/abs/film.mp4"},
//                      {"type": "still", "composition": "Film", "props": {...}, "frame": 120, "scale": 0.5, "out": "/abs/01.png"}]}
// Every console line a composition prints that starts with SAFE_BREACH, FONT_ERROR or UNKNOWN_KIND is
// collected into the report with the job it came from.
import {bundle} from '@remotion/bundler';
import {ensureBrowser, openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const started = Date.now();
const findings = [];
const timings = [];

const onBrowserLog = (job) => (log) => {
  const text = String(log.text ?? '');
  if (/^(SAFE_BREACH|FONT_ERROR|UNKNOWN_KIND)/.test(text)) findings.push({job: job.out, text});
};

await ensureBrowser();
const serveUrl = await bundle({
  entryPoint: path.join(here, 'src', 'index.ts'),
  publicDir: spec.publicDir,
  outDir: path.join(spec.bundleDir ?? path.join(os.tmpdir(), 'lh-bundle'), String(process.pid)),
});
const bundled = Date.now();
const browser = await openBrowser('chrome', {chromiumOptions: {gl: spec.gl ?? 'swangle'}});
const concurrency = spec.concurrency ?? Math.max(1, Math.min(16, Math.floor(os.cpus().length / 2)));

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
      codec: 'h264', crf: job.crf ?? 18, pixelFormat: 'yuv420p', x264Preset: job.preset ?? 'medium', muted: true,
      concurrency, onBrowserLog: onBrowserLog(job), chromiumOptions: {gl: spec.gl ?? 'swangle'},
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
