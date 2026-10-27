# Rain Radar

## What this makes

A live rain radar page for the person's place, as one folder of static files. The map of their town (or their
region) lies tilted under the camera with the place as a pulsing marker in the middle, and the last two hours of
radar plus the thirty-minute nowcast play over it as one loop: each frame crossfades into the next at full frame
rate, and every rain cell carries a soft glow. A comet playhead runs along the scrubber; dragging it or tapping a
step pauses on that moment. A few thousand wind streaks flow over the map, carried by a wind field read from a
seven-by-seven grid of forecast points around the place. A banner counts down to the rain ("Rain arriving in 24
min"), and the strip beside it shows the next hour of forecast rain, five minutes to a bar. It has a night look and
a paper look, works on phones and desktops, and keeps the person's place, layers, units, and loop speed on their
device. Without a connection, or with `"sample": true`, it plays a sample loop of a squall line moving in over a map
drawn for the place.

## Run

Make `rain-radar.inputs.json` in the person's project folder (copy `inputs.example.json` from this folder and change
the values; every key is explained in its `"_notes"`), then:

```
cd <project> && python3 <agent-apps root>/rain-radar/scripts/run.py
```

It writes `out/rain-radar/` in the project and prints the line to serve it. A missing or wrong key stops the run with
one plain line naming the key; fix the file and run it again. Running it twice on the same inputs gives the same
files.

## Check

- `out/rain-radar/index.html`, `out/rain-radar/config.js`, `out/rain-radar/theme.css`, and the sixteen sample frames
  in `out/rain-radar/sample/` exist.
- `out/rain-radar/config.js` holds the `place`, `lat`, `lon`, and `zoom` from the inputs.
- Serve the folder (Host, below) and open `http://localhost:8000/?demo=1`: the sample rain loops over the tilted
  map, wind streaks flow, the comet runs along the scrubber, the banner reads "Rain arriving in" with a count of
  minutes, and the browser console shows no errors.
- Open `http://localhost:8000/` with `"sample": false`: the radar is the live one, and the credits at the bottom say
  "Radar RainViewer", "Wind and rain Open-Meteo", and the map's credit.

## Host

The page is served, never opened as a file, because browsers refuse to load its modules from a file address.

```
cd <project> && python3 -m http.server 8000 --directory out/rain-radar
```

Then open `http://localhost:8000/`. Any static host takes the `out/rain-radar/` folder as it is. The 3D library and
the font ship in the folder; the live page asks RainViewer for the radar, Open-Meteo for the wind and the rain
forecast, and CARTO for the map tiles, none of which needs a key.

## Make it yours

Ask the person, in one message: "Where are you, should the map show your town or your whole region, and do you want
the dark look, the paper look, or the one that follows your device?"

1. **Where.** `"place"` is the name shown at the top; look up its `"lat"` and `"lon"` and write them as numbers.
2. **Town or region.** `"zoom"` is `town` (about 250 km across) or `region` (about 1,000 km across).
3. **The look.** `"theme"` is `dark` (the night map, rain lit and glowing), `paper` (a pale paper map with the rain
   laid on as watercolor), or `auto` (night in dark mode, paper in light mode).
4. **Optional:** `"units"` is `imperial` (in/h and mph) or `metric` (mm/h and km/h); `"layers"` picks the layers on at
   the start from `radar`, `wind`, and `clouds`; `"sample": true` plays the sample loop and never asks the live feeds.

Write the answers into `rain-radar.inputs.json`, set `"sample"` to `false` for the live radar, run the Run line
again, and serve it. The person can change the place, the layers, the loop speed, and the units later in Settings.

Changes past the inputs are plain files in `site/`: the colors of both looks are tokens in `site/themes/<name>.css`
(the `--map-*` tokens color the map, the `--color-rain-*` tokens the legend, the `--color-*` tokens the panels), the
map shader with the radar glow is `site/scene/ground.js`, the wind streaks are `site/scene/wind.js` (`SPEED` sets how
fast they run), the loop's timing is `site/game/loop.js`, and the sample rain is drawn by `draw_sample` in
`scripts/run.py`. Run the Run line after any change, since it copies `site/` fresh each time.
