# Glass Chess

## What this makes

A chess web page with pieces of clear and smoke glass on a lacquered, mirror-polished board. You play a friend on one
screen or the computer at one of four levels, with an optional clock, and the page opens playing Légal's famous mate
from 1750 until you start your own game.

## Run

```
cd <project> && python3 <agent-apps folder>/glass-chess/scripts/run.py
```

It reads `glass-chess.inputs.json` from the project folder, or `inputs.example.json` when the person has not made one
yet, and writes the page to `<project>/out/glass-chess/`. A missing or wrong key stops the run with one plain line
naming it and exit code 2. Running it again on the same inputs gives the same folder.

## Check

- `out/glass-chess/index.html`, `out/glass-chess/config.js`, and `out/glass-chess/theme.css` exist.
- `out/glass-chess/config.js` holds the player names and the theme from the inputs file.
- Served (see Host), the page opens with a glass board playing itself, the panel shows "Légal's mate", and the two
  buttons "Play the computer" and "Play a friend" start a game.

## Host

The page is served, never opened as a file:
`cd <project> && python3 -m http.server 8000 --directory out/glass-chess`, then open `http://localhost:8000/`.
Any static host takes the `out/glass-chess/` folder as it is. Games in progress and the chosen settings stay in the
browser on that device, under the key `glass-chess:state`; nothing is sent anywhere.

## Make it yours

Ask for these in one message, and default the rest from `inputs.example.json`:

- `title`: the name at the top of the page and in the browser tab.
- `players`: `{ "white": "…", "black": "…" }`, the names on each side; `"computer"` makes that side the computer.
- `strength`: the computer's level, 1 to 4. Level 1 plays loosely, level 4 thinks for up to two seconds a move.
- `theme`: `glass-noir` (black lacquer, clear and smoke glass), `glass-amber` (walnut and amber glass), or `ice`
  (white marble and blue glass). Each has a light and a dark look that follows the device.
- `clock`: `none`, `5+0`, `10+0`, or `15+10` (fifteen minutes and ten seconds added after each move).
- `sound`: `true` for the glass set-down, capture, and check sounds; `false` for silence.

The person can change the opponent, side, level, clock, board, and sound later from the page's Settings. To restyle a
board, edit its file in `site/themes/`: every color, the board's woods and lacquers, and the glass tints are tokens
there.
