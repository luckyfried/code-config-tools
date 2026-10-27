# reversi-table

## What this makes

A Reversi table in 3D that runs in the browser: lacquered discs that flip outward in waves from every placed disc, two trays of real disc stacks that keep the score, and a computer opponent at three strengths, or a friend on the same screen. The page opens on a finished game replaying itself, with the setup beside it; games save on the device.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/reversi-table/scripts/run.py
```

It reads `reversi-table.inputs.json` in the project folder. When the person has none yet, copy `inputs.example.json` from this app's folder to `<project>/reversi-table.inputs.json` first; it runs as is. The page is written to `out/reversi-table/` in the project folder, and the script prints the line that serves it. A missing or wrong key is named in one plain line and nothing is written.

## Check

Serve the folder (the Host line below) and open `http://localhost:8000/`. Within a second the board shows the opening four discs, and the replay starts: discs fill the board, a pass rattles a tray, one move turns thirteen discs along three lines, and the game counts out to "White wins" and "42 to 22". `out/reversi-table/config.js` carries the title, the players, and the strength; `theme.css` is the chosen table. `http://localhost:8000/game/test.html` checks the rules and the engine and reads "4 of 4 pass".

## Host

The page is a folder of static files, so it keeps running anywhere that serves files. On this computer:

```sh
cd <project> && python3 -m http.server 8000 --directory out/reversi-table
```

then open `http://localhost:8000/`. Serve it rather than opening `index.html` as a file, because browsers refuse its modules from a file. Any static host (GitHub Pages, Netlify, a web server's folder) takes `out/reversi-table/` as it is, at any path. Games and settings stay in that browser on that device.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com; it sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `out/reversi-table/index.html` (or from `site/index.html` here, so every run leaves it out).

## Make it yours

Ask in one message: the page's title, the two players' names (or "computer" for one side and how strong it plays), and the table. Then write `<project>/reversi-table.inputs.json` and run again. Every key:

- `title`: the page's name.
- `players`: `{ "black": "Ada", "white": "computer" }`. Black moves first. `"computer"` makes that side the engine; two names make it a game for two people on one screen.
- `strength`: 1 (Easy), 2 (Club), or 3 (Master): the computer looks 2, 4, or 6 moves ahead, and Master plays the last ten empty squares perfectly.
- `theme`: `lacquer-green` (ivory and black on green), `walnut` (cream and espresso on wood), or `neon` (cyan and magenta on black glass, with the reflection turned up). Each has a day and a night look that follows the device, and the person can switch tables in the page's settings.
- `sound`: `true` plays the disc ticks; `false` keeps the table quiet.

Nothing here needs a build step or a network: Three.js, the studio lighting, the font, and the sounds ship in `site/`. A new table is one more file in `site/themes/` with the same tokens (the 3D table reads its colors from them); swatches for it go in `site/index.html`. The rules live in `site/game/reversi.js`, the computer in `site/game/engine.js`, the disc and flip timing in `site/game/table.js`, and the 3D pieces in `site/scene/`.
