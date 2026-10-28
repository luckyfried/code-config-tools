# Sky Tonight

## What this makes

A planetarium page for one place: the stars, constellations, planets, and Moon as they stand over that place tonight, or at any date and hour, above a horizon with the compass points. The page also has a Tonight card with sunset, full dark, the Moon's phase and rise or set, and the planets that are up. The page opens on the night's best-known constellation while its lines draw on, then turns two hours forward and back so the stars leave trails. Drag to look around, scroll or pinch to zoom, slide the time ribbon, tap a star for its name, distance, and constellation, and on a phone hold it up to the sky.

## Run

Run this from the project folder before asking the person anything. It uses `sky-tonight.inputs.json` in that folder when it exists; when it does not, copy `inputs.example.json` from this app folder to `sky-tonight.inputs.json` first, and the sample sky over Flagstaff, Arizona is written.

```sh
cd <project> && python3 <agent-apps root>/sky-tonight/scripts/run.py
```

It writes the page to `out/sky-tonight/` in the project folder. It needs only Python 3. A missing or wrong key is named in one plain line, and the script exits with code 2.

## Check

The run prints two lines. The first gives how high Polaris stands over the place at the chosen time, which matches the latitude to within about half a degree. The second names the folder and its file count. `out/sky-tonight/index.html` exists, `out/sky-tonight/config.js` holds the place, `lat`, and `lon`, and the star catalog (`vendor/d3-celestial/data/`) and the Milky Way panorama (`vendor/eso/`) are in the folder. Served (see Host), the page shows the sky with named constellations over the horizon. In its first seconds the lines draw on, then the time ribbon runs two hours forward and back while the stars trail.

## Host

The page has to be served, not opened as a file. On this computer:

```sh
cd <project> && python3 -m http.server 8000 --directory out/sky-tonight
```

Then open `http://localhost:8000/`. Any static host can serve the `out/sky-tonight/` folder as it is, at any address or subpath. The page calls no service and works with no network.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com. It sends no data. Remove the `<script src="./badge.js"></script>` line from `index.html` to take it off.

## Make it yours

Ask the person, in one message: where they are (a town or coordinates), whether they want constellation lines and names on, and whether they like deep night, red light (keeps eyes adapted to the dark at a telescope), or a paper star chart. Then edit `sky-tonight.inputs.json` in the project folder and run again; no Node or build step is needed for any of these keys:

- `place`: the name at the top of the page; the part before a comma is the title.
- `lat`, `lon`: the place's coordinates in degrees, north and east positive.
- `timezone`: the IANA time zone of the place, such as `America/Phoenix` or `Europe/London`. Work it out from the place.
- `when`: `"now"` for the live sky (it opens on tonight after dark when it is still light), or a local date and time like `"2027-03-12T20:45"`. The sample uses a March evening over Flagstaff, when Orion, the Pleiades, and a crescent Moon are in the west.
- `horizon`: `"hill"`, `"sea"`, `"city"`, or `"flat"`, the skyline drawn around the viewer.
- `labels`: `"names"`, `"bayer"` (Greek letters on the stars), or `"none"`.
- `constellations`: `"lines"`, `"art"` (wide painted strokes), or `"none"`.
- `theme`: `"night"`, `"red"`, or `"paper"`. Each is a file in `site/themes/` holding only colors. A new look is a new file there with the same token names, and its name goes in `theme`.

On the page, the settings button changes the place, date, time, labels, horizon, and look for the visit; the inputs file keeps the defaults. The time ribbon's position is not saved.

Changes that touch the page itself, such as a new sky object, a new layer, or a different silhouette, are edits to the plain JavaScript in `site/scene/` (the sky drawing) and `site/game/` (clock, view, labels, and panels). They need no build step either. The star data comes from d3-celestial (BSD-3) and HYG (CC BY-SA 4.0), the Milky Way panorama from ESO and S. Brunier (CC BY 4.0), the Moon map from NASA's Lunar Reconnaissance Orbiter, Three.js and astronomy-engine under MIT, and the fonts Cormorant Garamond and Atkinson Hyperlegible Next under the SIL Open Font License; the page's settings sheet credits them too.
