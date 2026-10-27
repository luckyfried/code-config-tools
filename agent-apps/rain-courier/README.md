# Rain Courier

## What this makes

A drone delivery game at `out/rain-courier/index.html` in your project folder: a city at night in the rain, built from a word you pick, with your city's name on its biggest rooftop signs. The page opens on the courier drone already flying a run between the towers. Press Start shift to take the controls: hook a package on the lit roof, carry it to the lit balcony across town, and beat the shift clock. Every delivery adds 15 seconds, a crash costs 5, and passing within two meters of a wall at speed earns a near-miss bonus. It plays on a phone with two thumbs (a stick on the left, a climb slider on the right) and on a computer with W A S D, Space to climb, Shift to drop, and a drag to look. The best shift is kept in the browser on that device.

## Run

Run this from the person's project folder before asking them anything, so they see the game right away:

```sh
cd <project> && python3 <agent-apps root>/rain-courier/scripts/run.py
```

It reads `rain-courier.inputs.json` from the project folder. When that file is not there yet, copy `inputs.example.json` from this app's folder to `<project>/rain-courier.inputs.json` first and run again. The run writes `out/rain-courier/` in the project folder and prints the line to serve it. A missing or wrong key is named in one plain line and nothing is written.

## Check

- `out/rain-courier/` holds `index.html`, `config.js`, `theme.css`, and `models/drone.glb`; `config.js` contains the `cityName` from the inputs file.
- Served as the Host section says and opened in a browser, the city shows lit windows and falling rain at once, the drone is flying, and a glowing route ribbon runs from the drone to a lit roof with a column of light over it. Within ten seconds the drone reaches the roof and lifts the package on its rope.
- Press Start shift: the clock counts down from the shift length at the top left and the objective shows the pickup or drop with its distance.

## Host

The page must be served, not opened as a file, because browsers refuse its modules from a file address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/rain-courier
```

Then open `http://localhost:8000/`. Any static host can serve the `out/rain-courier/` folder as it is, at any address or subfolder; everything it needs, including the 3D library, the drone model, the fonts, and the sounds, is in the folder, and it makes no request to anywhere else.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `index.html` (and `badge.js` itself if you like).

## Make it yours

Ask in one message: "What's your name, what's the city called, and which night (neon, amber, or ghost)?" Then write their answers into `<project>/rain-courier.inputs.json` and run again. Every key:

- `title`: the name on the dispatch screen and the browser tab.
- `pilotName`: the pilot's name on the dispatch screen and the shift-over card.
- `cityName`: painted on the biggest rooftop signs and shown on the dispatch screen; up to 22 characters reads best.
- `theme`: `neon` (pink and cyan signs), `amber` (sodium streetlight orange with teal signs), or `ghost` (white and green on black). Each has a dusk look for light mode and a night look for dark mode, and the theme recolors the signs, windows, fog, street, drone trim, and screens.
- `seed`: any word; the streets, towers, signs, and routes are built from it, and the same word always builds the same city.
- `shiftSeconds`: the shift's length in seconds, from 20 to 600; 90 is the standard shift.

None of these need anything installed: change the inputs file, run again, and serve. For deeper changes, edit the app's files and run again:

- A new night: copy a file in `site/themes/`, change its colors (the `--scene-*` tokens color the world, the `--color-*` tokens color the screens), and name it in `theme`.
- The sign words: `SIGN_WORDS` and `VERTICAL_WORDS` at the top of `site/game/gen.js`.
- How the drone flies: the numbers at the top of `site/game/flight.js`; the time a delivery adds and a crash costs: the top of `site/game/main.js`.
- The sounds: `python3 scripts/sounds.py` from this app's folder renders them again into `site/audio/`.
