# Era Timeline

## What this makes

A timeline page the person can pan and zoom, of whatever they are keeping: a family's generations, a project's history, a course's periods. Eras are translucent layered bands, events are pins in lanes that never overlap and open a card with text, a picture, and the era, and a story mode walks every event in order. The axis relabels itself from centuries down to days as you zoom, a minimap shows where you are, phones get the same timeline running down the screen, and the whole thing prints as one long strip.

Before asking for anything personal, ask in one message: "What is the timeline of? What are its eras, with rough dates? Give me ten to thirty events with a date and a line each, and any pictures you'd like on them."

## Run

From the person's project folder, with their inputs file there (when there is none yet, copy `inputs.example.json` from this app folder to `era-timeline.inputs.json` in the project first; it holds a sample family timeline that renders as is):

```sh
cd <project> && python3 <agent-apps root>/era-timeline/scripts/run.py
```

It reads `<project>/era-timeline.inputs.json` and writes the page to `<project>/out/era-timeline/`. A missing or wrong key is named in one plain line and the run stops with exit code 2; nothing is written until the inputs are right. Running it again on the same inputs writes the same files.

## Check

The run prints `Wrote out/era-timeline/ (<n> files)`. Serve the folder (see Host) and open it: the title is at the top, the eras are colored bands, and every event is a pin on the axis. Scroll or pinch to zoom and the axis labels change from decades to years, months, and days; tap a pin and its card opens; Story walks every event; Print shows the long strip. `out/era-timeline/data.js` holds every era and event, and `config.js` the title, the first view, the orientation, the theme, and autoplay.

## Host

The page is a static folder, so it keeps running anywhere that serves files. It is served, never opened as a file, because browsers refuse its modules from a `file://` address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/era-timeline
```

Then open `http://localhost:8000/`. Any static host (GitHub Pages, Netlify, Cloudflare Pages, a web server's folder) can take `out/era-timeline/` as it is, at the root or under a subpath. Nothing is fetched from anywhere else: the fonts, the pictures, and the code are all in the folder.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data anywhere. To remove it, remove its script line, `<script src="./badge.js"></script>`, from `site/index.html` in this app folder and run again.

## Make it yours

Every key below lives in `<project>/era-timeline.inputs.json`; change it and run again. None of them needs anything but Python.

- `title`, `subtitle`: the name at the top and the line under it.
- `eras`: `{ "label", "from", "to", "color" }` each. Dates are a year (`1911`), a month (`1911-05`), or a day (`1911-05-02`); `-500` is 500 BCE. `to` runs through the end of its year, month, or day. Colors are `red`, `orange`, `gold`, `green`, `teal`, `blue`, `violet`, or `rose`, drawn in each theme's own tones, or a `#rrggbb` color. Eras that overlap sit in separate layers, in the order listed.
- `events`: `{ "date", "label", "text", "image", "era" }` each; `text`, `image`, and `era` are optional. `image` is a path beside the inputs file (a `.jpg`, `.png`, `.webp`, `.gif`, `.svg`, or `.avif`), copied into `out/era-timeline/media/`; the sample pictures in this app's `sample/` folder can be named the same way. `era` names an era by its label; left out, the event takes the narrowest era its date falls in.
- `start`, `end`: the first view.
- `orientation`: `auto` (across on a wide screen, down on a tall one), `horizontal`, or `vertical`.
- `theme`: `parchment` (warm white, earth-toned bands, ink pins), `museum` (near-black, jewel-toned bands, bone pins), or `auto` (parchment in a light color scheme, museum in a dark one).
- `autoplay`: `true` opens on the story walk, which stops the moment the person touches the timeline; `false` opens still.

A new theme is a new file in `site/themes/` holding the same tokens as `parchment.css`; name it in `theme`. The page's structure and look are in `site/styles/` and its behavior in `site/js/`, plain files with no build step. `node --test tests/pinch.test.mjs` replays a recorded pinch and the lane layout against those modules.

Keyboard: arrows pan, `+` and `-` zoom, `Home` returns to the first view, `/` searches, `Escape` closes the top-most thing open, and in a story the arrows step through events.
