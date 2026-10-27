# Trail Replay

## What this makes

A page per activity from the person's GPX and TCX exports, in `out/trail-replay/`: the run, ride, or hike replays over real 3D terrain with a glowing track colored by pace, heart rate, or height, a marker with a comet tail, and a camera that follows behind and above. Elevation, pace, and heart-rate charts scrub together with the map, the splits table lights the split the replay is in, the Activities screen lists every activity with a mini route, and the Poster screen downloads the route as a 2400 by 3600 PNG.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/trail-replay/scripts/run.py
```

It reads `trail-replay.inputs.json` in the project folder. When there is none yet, copy this app's `inputs.example.json` there as `trail-replay.inputs.json` first; it replays the three sample activities that ship with the app (a 5.6 km trail run, a hike, and a ride in Boulder, Colorado), with no network.

The script parses every GPX and TCX file in the `activities` folder with Python's standard library, works out distance, climb, pace, heart rate, and splits, and writes one JSON per activity, the terrain tiles each route needs, `config.js`, and `theme.css` into `out/trail-replay/`. It prints each activity's distance and climb and the number of files written. Terrain tiles it downloads for the person's own routes are kept in `trail-replay-terrain/` beside the inputs file, so the next run reuses them. A missing or wrong key stops it with one plain line naming the key, and exit code 2.

## Check

- `out/trail-replay/index.html` exists, and `out/trail-replay/data/` holds `index.json` and one JSON per activity, with the distances and climbs the run printed.
- Served (see Host), the page opens on the most recent activity replaying: 3D terrain at a 60° tilt, the glowing track, the marker with its comet, and the camera following. The charts' cursors move with the marker; dragging a chart or its handle moves the replay.
- The map's credit line names the terrain sources (Mapzen, USGS 3DEP, NASA SRTM, and others); on a phone it sits behind the (i) button.
- Activities lists every file; Poster shows the route as one line on paper and downloads a PNG.
- A second run on the same inputs writes the same bytes.

## Host

The output is a static folder. Serve it, never open it as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/trail-replay
```

then open `http://localhost:8000/`. Any static host takes `out/trail-replay/` as it is, at any path. The page keeps only the last activity viewed, in the browser's own storage on that device. With `"labels": false` it fetches nothing beyond its own folder; for a person's own routes, any terrain tile the run could not download is fetched from the AWS terrain tiles while the page is online.

## Make it yours

Ask the person, in one message: where their activity exports are (a folder of GPX or TCX files; Strava, Garmin Connect, and Apple Fitness all export them), miles or kilometers, and which look they want: topo, night, or paper. Then set the keys in `trail-replay.inputs.json` and run again:

| Key | What it does |
|---|---|
| `athlete` | The name on the page and the poster. |
| `activities` | A folder beside the inputs file holding GPX and TCX files. `"samples"` uses the three that ship with the app. |
| `units` | `"km"` or `"mi"`; splits follow it. |
| `colorBy` | What colors the track first: `"pace"`, `"heart"`, or `"elevation"`. The page can switch it. |
| `theme` | `"topo"`, `"night"`, or `"paper"`. Each has a designed light and dark look that follows the device. |
| `labels` | `true` adds roads, water, and place names from OpenFreeMap (keyless) over the terrain while the page is online. |
| `strava` | `true` also pulls the last thirty Strava activities. It needs a Strava access token set through `csc key set STRAVA_ACCESS_TOKEN`, never pasted in chat; `run.py` reads it from the environment and never writes it into the output. |

No Node needed for any of these, nor for a new theme: a theme is one CSS file of shadcn color variables plus the map, chart, and poster colors (`--relief-*`, `--ramp-*`, `--poster-*`, and the rest) in `src/themes/`. Copy one, change the values, and name it in `theme`. The poster's paper and ink live in the same file.

Changing a screen, adding a chart, or adding a dependency edits `src/` and needs Node to rebuild `dist/`, from this app folder: `npm ci && npm run build`. Then remove `node_modules/` so it never rides along with the app. A new chart is one more entry in `METRICS` in `src/screens/ReplayScreen.tsx` with its series in `src/components/ProfileChart.tsx`.
