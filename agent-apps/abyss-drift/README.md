# abyss-drift

## What this makes

A two-minute dive at `out/abyss-drift/index.html`: a small submarine down a glowing trench, eight species living at their own depths, and a viewfinder and shutter that turn each sighting into a real PNG stamped with the species, the depth, the date, and the diver's name. The page opens on the live trench; the air includes the climb back up; the creature log and the best dive stay in the browser.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/abyss-drift/scripts/run.py
```

It reads `<project>/abyss-drift.inputs.json`. When that file is missing, copy `inputs.example.json` from this folder to `<project>/abyss-drift.inputs.json` first, run, and show the result; then ask in one message: "What's your name for the photos, which water (abyss, kelp, or volcanic), and a word to shape your trench from?" Put the answers in `diverName`, `theme`, and `seed`, and run again.

The output folder is `<project>/out/abyss-drift/`. A missing or wrong key stops the run with one plain line naming it and exit code 2; two runs on the same inputs write the same files.

## Check

`out/abyss-drift/` holds `index.html`, `config.js`, `theme.css`, and `models/submarine.glb`, and `config.js` carries the diver's name. Served (see Host) and opened in a browser, the page shows the live trench behind the title sheet. Press Dive and hold the dive button (Space on a keyboard): within a few seconds a creature lights up in the log strip, and a press of the shutter (Enter) adds a photo to the strip. After surfacing, the results list every photo with Save photo.

## Host

The page is served, never opened as a file, because browsers refuse its modules from a `file://` address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/abyss-drift
```

Then open `http://localhost:8000/`. Any static host serves the folder as it is, at any path. Nothing is fetched from anywhere else: Three.js, the fonts, the model, and the sounds all ship in the folder, and the log is kept in the browser's own storage.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `index.html`.

## Make it yours

Every key in `abyss-drift.inputs.json` changes the dive with no other tools; run `run.py` again after an edit:

- `title`: the name on the surface screen and in the corner of every photo.
- `diverName`: stamped on every photo as "Photo by …".
- `theme`: `abyss` (blue-black, cyan glow), `kelp` (green water, gold glow), or `volcanic` (red vents, orange glow). Each theme sets the water, the rock, the lichen, the creatures' glow, and the interface, with a light look and a dark look that follow the device.
- `seed`: any word; the trench's bends, its rock, and where the vents stand come from it.
- `airSeconds`: the dive's air, climb included, from 45 to 600 (120 is the standard dive).
- `species`: which of `whale`, `manta`, `school`, `jellyfish`, `lanternfish`, `anglerfish`, `squid`, and `crab` live in the trench, or `"all"`.

Further changes are plain files, and none of them needs Node or a build step:

- A new water: copy `site/themes/abyss.css` to `site/themes/<name>.css`, change the color tokens (the `--world-*` ones paint the scene), and set `"theme": "<name>"`.
- A different submarine: replace `site/models/submarine.glb` with any glTF about 4 m long facing +z. Name its paint material `hull` to have the theme color it.
- The sounds: `python3 scripts/make_sounds.py` renders every sound again into `site/audio/`, so a changed recipe in that script becomes a new file.
- The creatures live in `site/scene/creatures.js` and their depth bands in `site/game/species.js`; the light, fog, and post effects by depth are in `site/scene/world.js`.
