# Hours Ledger

## What this makes

A time tracker for a freelancer in one web page, built into `out/hours-ledger/` in your project. Today opens on the running timer: one card with the client's color across its top, a 64 px readout that counts the hours, and a dot that breathes while it runs. Tap another client's chip and the finished block slides down into the day's list as the new timer starts. Every entry edits in place: the note, the client, and the start and end times. Beside it, the week's bars rise by client color and the month's heat strip tints each day by its hours. Week and Month have their own screens with totals per client, and a tap on a day's bar opens that day's entries. Statement lays out one client's hours for a period on a printable page: the name and the period at the top, every entry with its rounded hours, and the hours × rate line with the total at the foot. An entry that has run more than twelve hours is flagged on Today with a one-tap way to end it. Add time takes a duration or a start and end time on any day, and the S key starts and stops the timer on a computer. Hours stay in the browser under the key `hours-ledger`, with Export CSV, Export JSON, and Import in Settings.

Ask the person, in one message: "Who are your clients, and what is your hourly rate for each? What currency do you bill in? Do you round time on statements to 6 minutes, 15 minutes, or not at all?" Then copy `inputs.example.json` from this folder to `hours-ledger.inputs.json` in the project folder and set `name`, `currency`, `clients` (each with an `id`, a `name`, a `rate`, and a `color`), `rounding` (`0`, `6`, or `15`), `weekStart` (`mon` or `sun`), `theme` (`studio`, `ledger`, or `auto`), and `statementNote`. `sample: true` fills a first visit with five weeks of example hours and a running timer; set it to `false` for a ledger that opens empty. `_notes` explains every key.

## Run

```
cd <project> && python3 <app>/scripts/run.py
```

It checks `hours-ledger.inputs.json`, names any key that is missing or wrong in one line each, and writes `out/hours-ledger/`. Running it again gives the same files.

## Check

Serve the folder (below) and open it. The client chips on Today list every client in `config.js`. Start a timer, wait a few seconds, stop it, and reload: the entry is in Today's list with a duration above zero. The Week bars carry `data-total`, the sum of the week's hours. On Statement, pick a client and print: the page shows the client's name, the period, and a line total equal to the rounded hours × the rate, with the rounding stated at its foot. Export CSV in Settings writes one line per entry under a header line. The browser console stays empty.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/hours-ledger
```

Then open http://localhost:8000/. The folder is static, so any file host serves it from any path.

## Make it yours

No Node needed: every input key, the theme, and the copy. Change `hours-ledger.inputs.json` and run `run.py` again. A theme is a file in `src/themes/` (`studio.css`, `ledger.css`); copy one, change its colors, and name it in `theme`. A client's `color` gives its hue; the theme sets the lightness and chroma every client shares (`--client-l`, `--client-c`), so any color lands in the theme's palette. `run.py` writes the chosen theme as `theme.css`, and adds the ledger paper the statement always prints on. The statement's foot line is `statementNote`.

Needs Node: a component, a page, a new column or report, or a dependency. Edit `src/`, then in this folder run:

```
npm ci
npm run build
rm -rf node_modules
```

Ship the new `dist/` with the change; `run.py` copies it as it is.
