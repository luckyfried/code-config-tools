#!/usr/bin/env python3
"""Builds the film's composition into motion/dist/, the static page scripts/render.py serves. Authoring only: node and
npm run here and nowhere else, and dist/ ships with the kit, so a person's machine never needs either.

USAGE (on the authoring machine, from anywhere):
    python3 scripts/dev/build_motion.py           # npm ci in motion/, bundle into motion/dist/

Run it after any change under motion/; what a stale bundle misses shows in the film. The bundle carries no public folder: render.py serves
the run's public/ (photographs, fonts, grain) at the page's static base, ./public. npm's cache is npm_config_cache when
it is set, else ~/.cache/code-config/<kit>/npm.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
MOTION = KIT / "motion"
DIST = MOTION / "dist"
SKIP = {"node_modules", "dist"}

# @remotion/bundler's bundle() over the studio entry, resolving every package from motion/node_modules, minified with
# esbuild and without source maps (a stack in the render log names the bundle's own lines), and without webpack's cache
# folder
BUNDLE = r"""
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [motion, outDir, publicDir] = process.argv.slice(2);
const modules = path.join(motion, 'node_modules');
const req = createRequire(path.join(motion, 'package.json'));
const {bundle} = await import(pathToFileURL(req.resolve('@remotion/bundler')).href);
const {default: Terser} = await import(pathToFileURL(createRequire(req.resolve('@remotion/bundler')).resolve('terser-webpack-plugin')).href);
await bundle({
  entryPoint: path.join(motion, 'studio', 'index.ts'),
  outDir, publicDir, enableCaching: false,
  webpackOverride: (config) => ({
    ...config,
    devtool: false,
    optimization: {...config.optimization, minimize: true, minimizer: [new Terser({minify: Terser.esbuildMinify})]},
    resolve: {
      ...config.resolve,
      modules: [modules, 'node_modules'],
      alias: {...(config.resolve?.alias ?? {}), react: path.join(modules, 'react'), 'react-dom': path.join(modules, 'react-dom'), remotion: path.join(modules, 'remotion')},
    },
  }),
});
"""


def run(argv, **kw):
    print("+ " + " ".join(argv), file=sys.stderr, flush=True)
    subprocess.run(argv, check=True, **kw)


def build():
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        sys.exit("node and npm are needed to build the bundle (authoring only); neither is needed to render")
    env = dict(os.environ, npm_config_update_notifier="false")
    env.setdefault("npm_config_cache", str(Path.home() / ".cache" / "code-config" / KIT.name / "npm"))
    run([npm, "ci", "--no-audit", "--no-fund", "--loglevel=error"], cwd=MOTION, env=env, stdout=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        out, empty = Path(tmp) / "dist", Path(tmp) / "public"
        empty.mkdir()
        # a file, not `node -e`: the minifier's workers start with node's own arguments and would run the script again
        script = Path(tmp) / "bundle.mjs"
        script.write_text(BUNDLE)
        run([node, str(script), str(MOTION), str(out), str(empty)], cwd=MOTION, env=env)
        shutil.rmtree(out / "public", ignore_errors=True)
        # the page names the folder it was built in; the bundle ships, so it names none
        html = out / "index.html"
        html.write_text(re.sub(r"window\.remotion_cwd = [^;<]*;", "window.remotion_cwd = null;", html.read_text()))
        shutil.rmtree(DIST, ignore_errors=True)
        shutil.copytree(out, DIST)
    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(json.dumps({"dist": str(DIST), "files": sum(1 for p in DIST.rglob("*") if p.is_file()), "bytes": size}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
