# Run Atlas

## What this makes

A page that draws every run, ride, walk, and hike you have recorded as a wall of route thumbprints: each route a single
line on its own square tile, all scaled to the same box. Tap a tile and the route flies open and draws itself at the
pace you ran it, with a pace strip colored kilometer by kilometer, the elevation profile, and the splits. Above the wall
sit the last twelve months as bars, the rolling total, and three personal bests (fastest 5 km, longest, most climb). A
Months screen shows every year month by month. It is built from the GPX files your watch or Strava exports, and nothing
leaves your computer.

## Run

Run this from the project folder before asking for anything personal; it shows the sample year that ships with the app:

```sh
cd <project> && python3 <agent-apps root>/run-atlas/scripts/run.py
```

`scripts/run.py` reads `run-atlas.inputs.json` from the project folder. When the person has no inputs file yet, copy
`inputs.example.json` from this folder to `<project>/run-atlas.inputs.json` first; its empty `"activitiesDir"` draws the
sample. The run writes the page to `out/run-atlas/` in the project folder and ends with the line to serve it. A missing
or wrong key stops the run with one plain line naming it, and exit code 2.

## Check

The run's last two lines read `Read <n> activities, <distance> in all; the monthly bars add up to the same.` and
`Wrote out/run-atlas/ (<n> files).` Serve the folder (see Host) and open `http://localhost:8000/`: the wall shows one
tile per GPX file, the bars above it rise month by month, the twelve-month total counts up, and on a wide screen the
newest activity opens beside the wall and draws itself. Tap any tile to see its route, pace strip, elevation, and
splits. `out/run-atlas/data.js` holds one entry per GPX file with its `points`, `distance` (meters), `duration`
(moving seconds), and `gain` (meters). A file Run Atlas cannot read is named in the run's output and left out.

## Host

The page is a folder of plain files, served, never opened as a file (browsers refuse its modules from a `file://`
address):

```sh
cd <project> && python3 -m http.server 8000 --directory out/run-atlas
```

Then open `http://localhost:8000/`. Any static host serves `out/run-atlas/` as it is, at any address or subpath; the
GPX files are copied into `out/run-atlas/media/activities/`, so a hosted page carries your routes with it.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A
tap opens the app's page on code-config.com; it sends no data. To remove it, remove the
`<script src="./badge.js"></script>` line from `out/run-atlas/index.html` (or from `site/index.html` in this folder, so
every run leaves it out).

## Make it yours

Ask the person, in one message: "Where are your GPX files (I can tell you how to export them from Garmin or Strava)?
Kilometers or miles? Runs only, or rides and walks too?" Then write their answers into
`<project>/run-atlas.inputs.json` and run again.

| Key | What it does |
| --- | --- |
| `activitiesDir` | The folder of GPX files, relative to the inputs file, such as `"activities"`. Files ending `.gpx` or `.gpx.gz` are read; `""` draws the sample year. |
| `units` | `"km"` or `"mi"`: distances, paces, splits, and climb (meters or feet). |
| `sports` | Any of `"run"`, `"ride"`, `"walk"`, `"hike"`; `[]` shows them all. |
| `year` | The year the wall opens on, such as `2026`; `null` opens on the latest. The page's year filter lists every year found. |
| `theme` | `"asphalt"` (near-black tiles, white routes, pace from blue to orange), `"trail"` (bone-white tiles, ink routes, pace from teal to rust), or `"auto"` (trail by day, asphalt by night, following the device). |

Getting the GPX files:

- **Strava:** Settings, My Account, "Download or Delete Your Account", Request your archive. The emailed zip has an
  `activities/` folder; point `activitiesDir` at it. Activities recorded as FIT files are left out and counted in the
  run's output; export those one at a time from the activity's menu, "Export GPX".
- **Garmin Connect:** open an activity, the gear menu, "Export to GPX". For many at once, Garmin's data export
  (Account, Data Management, Export Your Data) sends a zip of every activity.
- **Apple Fitness:** a workout exporter app (such as HealthFit or RunGap) saves workouts as GPX files.
- **Coros:** open the activity in the Coros app or Training Hub and export GPX.

The folder can keep growing: drop new files in and run again. The sport comes from each file's own type (Strava,
Garmin, and most exporters write one), else from its name, else from its speed. A file with no timestamps still gets a
tile, with its distance, route, and climb, and blank pace. A split faster than a person can go on that sport (a GPS
jump) is marked in the splits table and does not count toward the bests.

Changes that need nothing but a rerun: every key above, and the theme. To recolor, copy a file in `site/themes/` to a
new name, change its colors, and set `"theme"` to that name. The page itself is plain HTML, CSS, and JavaScript under
`site/` with no build step: `site/styles/` holds the layout, `site/app/` the wall, the activity, and the Months screen.
