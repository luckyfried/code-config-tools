# Numbers Wall

## What this makes

One page with the numbers you watch, as a wall of tiles. Each tile shows the latest figure in large type, the change
since the reading before it (green when it is good news, red when it is not), and a sparkline of the last thirty
readings with the goal drawn as a thin line. A tile's edge lights up once its goal is met. Click or tap a tile to see
its whole history and every reading in a table.

Tiles are 1x1, 2x1, or 2x2, so the numbers that matter most are the biggest. Press F for TV mode (just the tiles,
sized to read from across a room, over a slow moving background); Escape leaves it. A wall screen with no keyboard
opens straight into TV mode at `http://localhost:8000/#tv`. On a computer screen, a wall nobody touches goes to TV mode
by itself a few seconds after it opens (half a minute once someone has used it), and the first move of the mouse or a
key brings the wall back. Each group of tiles draws in its own color. On a phone the wall is one column of tiles, with
the biggest number first and biggest.

The numbers live in `numbers-wall.inputs.json` in your project. `inputs.example.json` is a full sample (a small tea
company's revenue, customers, and operations) and its `_notes` object explains every key.

## Run

```sh
cd <project> && python3 <agent-apps>/numbers-wall/scripts/run.py
```

`<project>` is the folder that holds `numbers-wall.inputs.json`; `<agent-apps>` is the folder this app sits in. The
run copies the page into `<project>/out/numbers-wall/` and writes the numbers and the theme beside it. Running it again
on the same file gives the same output.

To refresh the wall, add a reading to each metric's `history`, set `refreshedAt` to now, and run again. A metric with
a `source` gets its next reading by itself on each run (see Make it yours).

## Check

- The run prints `Wrote out/numbers-wall/ (<n> files).` and exits 0. A problem in the inputs file prints one plain
  line per problem, names the key, and exits 2.
- Served, the page shows one tile per metric, grouped under each heading, with a change chip on every tile that has
  two readings or more. A metric with one reading shows its number and the date of that reading.
- The footer says when the numbers were refreshed.
- F opens TV mode with the tiles alone; Escape returns. Left alone on a computer screen, the wall goes to TV mode by itself.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/numbers-wall
```

Then open `http://localhost:8000/`. The folder `out/numbers-wall/` is the whole site: any static host serves it as it
is, at any path. It needs no network once it loads.

## Make it yours

Without Node, by editing `numbers-wall.inputs.json` and running `run.py` again:

- every key in the file: the title, the groups, each metric's label, unit, format, size, goal, and history;
- `theme`: `auto` (light or dark from the system), `obsidian` (dark), `paper` (light), or `terminal` (green on
  black). A new look is a new file in `src/themes/`, copied from one there; its name becomes a `theme` value;
- `copy`: every other word on the wall (buttons, the footer, the tile screen);
- a `source` on a metric, which fetches its next reading on each run. `scripts/sources.py` has `csv_last_row` (the
  last row of a spreadsheet export) and `plausible_visitors`; a function added there for any other service is
  named the same way, `"source": {"from": "<function>", ...}`. A service key is set with `csc key set` and read from
  the environment; it is never written into the inputs file or the page.

With Node, for a new component, a change to a page, or a new dependency: edit `src/`, then from this folder run

```sh
npm ci && npm run build && rm -rf node_modules
```

`dist/` is the built page that `run.py` copies; `node_modules/` never stays in the folder.
