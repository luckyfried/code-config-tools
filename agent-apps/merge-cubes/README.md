# Merge Cubes

## What this makes

A swipe-and-merge number puzzle in 3D that the person can host anywhere. Glossy cubes sit on a dark glass tray on a lit pedestal and glow brighter as they climb from a matte cream 2 to a white-hot gold 2048. A swipe or an arrow key slides every cube; two matching cubes squash into one that pops, flares, and throws sparks, and each merge plays a mallet note one step up a pentatonic scale. Reaching 2048 dims the board while the winning cube rises and turns at full glow, then the game keeps going. It has a score and best score, one undo, boards from 3 × 3 to 6 × 6, and three looks, and it saves on the visitor's device. The page is `out/merge-cubes/index.html`.

## Run

Run this from the person's project folder before asking for any personal details, so they see the board right away:

```sh
cd <project> && python3 <agent-apps root>/merge-cubes/scripts/run.py
```

It reads `merge-cubes.inputs.json` from the project folder. If that file is not there yet, copy `inputs.example.json` from this app's folder to `<project>/merge-cubes.inputs.json` first and run again. The run writes the page into `out/merge-cubes/` and prints how to serve it. A missing or wrong key is named in one line, and nothing is written.

Then ask in one message: "What should the page be called, which look do you want (night gold, sorbet, or cyber), and do you want numbers on the cubes or twelve labels of your own, from smallest to biggest?" Put the answers into `merge-cubes.inputs.json` and run the same line again.

## Check

`out/merge-cubes/` holds `index.html`, `config.js` (with the person's `title`, `size`, `theme`, and `labels`), `theme.css`, and the sounds under `sound/`. Serve the folder (see Host) and open it: the tray is lit within a second, a crowded board plays itself up to 2048, and the first swipe or arrow key starts the person's own game with two cubes. `game/test.html` in the same folder runs ten fixed boards through the rules and should say "10 of 10 boards come out right."

## Host

The page has to be served, not opened as a file, because browsers refuse to load its modules from a file. On the person's computer:

```sh
cd <project> && python3 -m http.server 8000 --directory out/merge-cubes
```

and open `http://localhost:8000/`. To keep it running after the session, put the whole `out/merge-cubes/` folder on any static host (GitHub Pages, Netlify, Cloudflare Pages, or a plain web server); it needs nothing else. Games in progress, best scores, and settings stay in each visitor's own browser and are never sent anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `out/merge-cubes/index.html` (or from `site/index.html` in this app's folder, so every later run leaves it out).

## Make it yours

Every key in `merge-cubes.inputs.json` changes the page with no other tools: run the Run line again after editing it.

- `title`: the name at the top of the page and on the browser tab, up to 40 characters.
- `size`: the board a new visitor starts on, 3 to 6 cubes on a side. Visitors can change it in Settings.
- `theme`: `night-gold` (a dark glass tray, cubes from cream to white-hot gold), `sorbet` (a pale pearl tray, cubes from milk and mint to coral), or `cyber` (a black tray with cyan light lines, cubes from ice cyan to magenta, with more glow). Each has a day look for light mode and a night look for dark mode, and each recolors the whole stage, not only the buttons.
- `labels`: `"numbers"`, or a list of twelve short labels (up to 14 characters each) shown on the cubes instead of 2, 4, 8, and on up to 4096: emoji, team names, or the person's own milestones. The climb beside the board shows them in order.
- `sound`: `true` to play a mallet note for each merge, `false` to start silent.

Deeper changes are plain files in this app's folder and need no build step:

- A new look: copy `site/themes/night-gold.css` to a new name and change its values. `--cube-1` to `--cube-12` color the cubes from 2 to 4096, `--cube-ink-N` their numbers, `--cube-glow-N` (0 to 1) how much each glows, and `--cube-heat-N` the color it glows in (the cube's own color when left out); `--scene-glow-power` sets how hot that glow burns, `--scene-halo-power` how much light the high cubes throw round themselves on the tray, and `--scene-halo-blend: over` lays that light on as a warm haze, for a pale stage where added light would not show; `--scene-pool-power` sets how brightly each lit cube spills its own light onto the tray round its foot, and `--scene-spark-power` how hot a merge's six sparks burn; the other `--scene-*` values color the tray, pedestal, floor, and lights and set the bloom. Set `theme` to the new name.
- The stage and the motion: `site/scene/` holds one file per part (`tray.js`, `cubes.js`, `fx.js`, `lights.js`, `camera.js`); the slide time, lean, pop, and drop are named at the top of `cubes.js`.
- The rules: `site/game/board.js`, with its ten fixed boards in `site/game/board.test.js` (run `node site/game/board.test.js`).
- The sounds: `scripts/make_sounds.py` renders the four WAV files in `site/sound/` with Python's standard library; change a note there and run `python3 scripts/make_sounds.py` from this app's folder.

The fonts are Bricolage Grotesque and Instrument Sans under the SIL Open Font License (`site/fonts/`); Three.js is MIT (`site/vendor/LICENSE`).
