# Lift Log

## What this makes

A strength training log in one web page, `out/lift-log/`, built for a phone on a gym bench. Pick the lift, set the weight and reps with big steppers (hold one to make it run faster), and log the set. "+ set" repeats the last set in one tap. The bar sits large at the top of the session: as the weight changes, the plates for each side slide onto the sleeve and stop against the collar, sized and colored like calibrated plates.

Every set is kept in the browser the page was opened in. A set that beats the lift's best estimated one-rep max (e1RM, by the Epley formula) sends a gold sweep across the whole screen and a "PR" chip. A thin bar across the top of the screen drains over the rest and ends with a two-tone chime. History shows each lift's sets by date and its e1RM curve, with a glowing dot on every record. Week tints a front and back body map, fourteen muscles, by the sets each got over the last seven days, and lists sets and volume per muscle. Settings changes units and rest, and exports or imports the log as a file. On a laptop the page is three panes: the week and your lifts, the session, and the chart for the selected lift.

Until the browser has a set of its own, the page shows a six-week sample log and says so in one line under the greeting. The first set logged starts the person's own log.

It needs one file in your project, `lift-log.inputs.json`. `inputs.example.json` in this folder shows every key with a note on each:

- `name`: the name the greeting uses.
- `units`: `kg` or `lb`.
- `exercises`: the lifts, each with an `id`, a `label`, the `muscles` it trains (the main one first), and its `equipment` (`barbell`, `dumbbell`, `machine`, or `bodyweight`; barbell shows the loaded bar). The muscles are chest, shoulders, biceps, triceps, forearms, traps, lats, abs, obliques, lower-back, glutes, quads, hamstrings, and calves. The example has twenty common lifts.
- `restSeconds`: the default rest timer.
- `plates`: the plate sizes the person has, for the bar drawing.
- `barWeight`: the bar.
- `theme`: `iron` (warm black, ember red, gold records), `chalk` (chalk-white paper, graphite type, iron red, amber records), or `auto` (chalk by day, iron when the device is set to dark).

Ask the person, in one message: "Kilograms or pounds? What are your main lifts, and what plates do you have? How long do you like to rest between sets?" Keep the example lifts they use, add their own with the muscles each trains, and drop the rest.

## Run

```sh
cd <project> && python3 <agent-apps root>/lift-log/scripts/run.py
```

Run it from the project folder, first on the example, before asking the person for anything. It reads `lift-log.inputs.json` there; when the person has none yet, copy `inputs.example.json` from this folder to `<project>/lift-log.inputs.json` first. It checks every key, and writes `out/lift-log/`: the built page, `config.js` with the inputs, and `theme.css` with the chosen theme. A missing or wrong key is named in one plain line and nothing is written. Running it again on the same inputs writes the same files.

## Check

1. `out/lift-log/config.js` holds the units and every exercise from the inputs.
2. Serve the page (see Host) and open it. It opens on the sample week: the body map shades in region by region, the bench press card shows a PR chip, and the rest bar drains across the top.
3. Log two sets of one lift, the second heavier: the PR chip comes in on the second. Reload the page: both sets are still there and the sample line is gone.
4. Open History for that lift: one point per session on the e1RM line, at its best set, a glowing gold dot on each record, and the Epley formula in the tooltip on "Best e1RM".
5. Open Week: fourteen muscles on the map, shaded by this week's sets.
6. In Settings, Export, then Clear the log, then Import the file: the sets come back as they were.
7. The browser console shows no errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/lift-log
```

Then open http://localhost:8000/. The page must be served this way, not opened as a file. The folder is plain files, so any static host serves it as it is, and a phone on the same network opens it at this computer's address on port 8000. The log lives in the browser on the device where it was logged; Export in Settings saves it as a file, and Import brings it to another browser. The export is also what to read when the person asks how the month went.

## Make it yours

These need no Node, only a new run of `run.py`:

- Every key in `lift-log.inputs.json`: the name, units, lifts and their muscles, rest, plates, bar, and theme.
- A theme: copy `src/themes/iron.css` or `src/themes/chalk.css` to a new file in `src/themes/`, change its colors, and set `theme` to the file's name. Every color on the page comes from those variables, the body map's five shades (`--map-0` to `--map-4`) and the record gold (`--pr`) included.
- The body map: `dist/body.svg` is the drawing, one `path` per muscle with a `data-muscle` name. Redraw a region and keep its name; make the same change in `public/body.svg` so a rebuild keeps it.

These change the page itself and need Node 20 or newer. Edit `src/`, then run the three commands from this folder:

```sh
npm ci && npm run build && rm -rf node_modules
```

- A component, such as the steppers (`src/components/Stepper.tsx`), the loaded bar (`src/components/Barbell.tsx`), or the chart (`src/components/E1rmChart.tsx`).
- A screen or a field on a set, such as an RPE number (`src/lib/lift.ts`, `src/components/SessionCard.tsx`).
- A dependency: add it with `npm install <name>` before the build.

The build writes `dist/`, which `run.py` copies into `out/lift-log/`; commit `dist/` with the change.
