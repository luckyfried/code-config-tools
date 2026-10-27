# Marble Canyon

## What this makes

A marble time trial the person can host anywhere: a glass marble rolls down a banked ribbon track through a sandstone canyon, with jumps, boost pads, and three checkpoint gates. Every run after the first races a see-through ghost of their best. The canyon is built from a word they choose, and the gold, silver, and bronze times come from the track's length. The page is `out/marble-canyon/index.html`.

## Run

Run this from the person's project folder before asking for any personal details, so they see their canyon right away:

```sh
cd <project> && python3 <agent-apps root>/marble-canyon/scripts/run.py
```

It reads `marble-canyon.inputs.json` from the project folder. If that file is not there yet, copy `inputs.example.json` from this app's folder to `<project>/marble-canyon.inputs.json` first and run again. The run writes the page into `out/marble-canyon/` and prints how to serve it. A missing or wrong key is named in one line, and nothing is written.

Then ask in one message: "What's your name, which look (canyon, ice, or neon), what color marble, and how long a track (short, medium, or long)?" Put the answers into `marble-canyon.inputs.json` and run the same line again.

## Check

`out/marble-canyon/` holds `index.html`, `config.js` (with the person's `racerName` and `seed`), `theme.css`, and the environment lighting under `env/`. Serve the folder (see Host) and open it: the title card sits over the marble already rolling through the canyon. Tap Roll (or press Space), and the countdown runs, the marble rolls through the first gate, and a finished run shows a time and a medal. Race the ghost starts a second run with the first one rolling beside you as a see-through marble.

## Host

The page has to be served, not opened as a file, because browsers refuse to load its modules from a file. On the person's computer:

```sh
cd <project> && python3 -m http.server 8000 --directory out/marble-canyon
```

and open `http://localhost:8000/`. To keep it running after the session, put the whole `out/marble-canyon/` folder on any static host (GitHub Pages, Netlify, Cloudflare Pages, or a plain web server); it needs nothing else. Best times and ghosts stay in each visitor's own browser and are never sent anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `out/marble-canyon/index.html` (or from `site/index.html` in this app's folder, so every later run leaves it out).

## Make it yours

Every key in `marble-canyon.inputs.json` changes the page with no other tools: run the Run line again after editing it.

- `title`: the name on the title card.
- `racerName`: shown on the result card and beside the ghost's time difference.
- `theme`: `canyon` (sandstone and a teal sky), `ice` (blue glass, a white track, a pale sun), or `neon` (a dark track with light strips). Each look has a daytime version for light mode and an evening version for dark mode, and recolors the whole canyon, not only the buttons.
- `seed`: any word. The same word always builds the same canyon, so two people on one hosted copy race the same track. Leave it out to use the racer's name.
- `trackLength`: `short`, `medium`, or `long`, about 40, 70, or 110 seconds at a good pace.
- `marbleColor`: the swirl inside the glass, as a hex color such as `#2f6fdb`.

Deeper changes are plain files in this app's folder and also need no build step:

- A new look: copy `site/themes/canyon.css` to a new name, change its colors (the `--scene-*` values color the canyon, the track, the sky, and the light; `--scene-env` names the lighting file in `site/env/`), and set `theme` to the new name.
- The marble, track, or canyon: `site/scene/` holds one file per part (`marble.js`, `track.js`, `canyon.js`, `sky.js`, `materials.js`, `post.js`).
- The feel: `site/game/rail.js` holds the speed, steering, boost, and jump numbers in `TUNING`; `site/game/generate.js` holds the track lengths, widths, and medal times.

The lighting files in `site/env/` are CC0 environments from Poly Haven; the display font is National Park under the SIL Open Font License (`site/fonts/OFL.txt`); Three.js is MIT (`site/vendor/LICENSE`).
