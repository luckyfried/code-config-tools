# net-worth-ledger

## What this makes

A one-page net worth chart that grows by one point a month. Assets stack above the zero line, debts mirror them below, and net worth runs as a bold line across both, with a flag where it first crosses each milestone. A scrubber under the chart picks a month: the headline number rolls to it and a donut redraws that month's accounts. A second view, Table, lists every month as a row and every account as a column, with each month's change colored by whether it helped or hurt.

Each month, ask the person for that month's balances, add one snapshot to the inputs file, and run again.

## Run

From the person's project folder, before asking for any balances:

```sh
cd <project> && python3 <agent-apps root>/net-worth-ledger/scripts/run.py
```

It reads `net-worth-ledger.inputs.json` from the project folder. When the person has none yet, copy `inputs.example.json` from this app folder to `<project>/net-worth-ledger.inputs.json` first and run on that: it draws a 22-month sample ledger, so the page works before anything personal is asked.

Then ask, in one message: "What currency? Which accounts do you want on the chart, and is each an asset or a debt? What are this month's balances?" Write the answers into the inputs file (`currency`, `accounts`, one entry in `snapshots`, and a `title` such as "Our household"), remove the sample snapshots, and run again.

Every later month, add one entry to `snapshots`, for example `{"month": "2026-11", "balances": {"checking": 5200, "card": 900}}`, and run again. An account left out of a month counts as zero.

The run writes `<project>/out/net-worth-ledger/`. A missing or wrong key stops it with one plain line naming the key, and exit code 2.

## Check

The run prints `Wrote out/net-worth-ledger/ (… files)`. Serve the folder as Host says and open it:

- The chart sweeps in from the left and the headline counts up to the latest month's net worth, which equals that month's assets minus its debts. The run checks that sum, and the headline carries it as `data-net`.
- There is one tick under the chart for every snapshot, and `out/net-worth-ledger/data.js` lists every snapshot with its totals.
- Dragging the scrubber or the chart moves between months; the arrow keys do the same once the scrubber has focus.
- Table shows every month, newest first.

## Host

The page is a static folder. Serve it, never open it as a file, because the browser refuses its modules from a file address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/net-worth-ledger
```

Then open `http://localhost:8000/`. Any static host takes the folder as it is, under any path. The page calls no outside service and sends nothing anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `site/index.html` in this app folder and run again.

## Make it yours

Every change below is a change to `<project>/net-worth-ledger.inputs.json` and a run; nothing needs installing. `inputs.example.json` explains each key in its `_notes`.

- `title`: the line under the app's name, such as "Our household".
- `currency`: any ISO code, such as "EUR" or "GBP". Amounts are written in the viewer's own number format.
- `accounts`: each with an `id`, a `label`, a `kind` of `asset` or `liability`, and a `color` of `auto` (the theme's blues for assets and warm oranges for debts) or a hex color.
- `snapshots`: one per month, `month` as `YYYY-MM`. Owed amounts are positive numbers.
- `milestones`: flags such as `{"label": "First 100k", "value": 100000}`, drawn where the net worth line first crosses the value.
- `theme`: `statement` (light, paper), `graph` (dark, black), or `auto` to follow the device.

When debts dwarf assets (a mortgage, say), each side of the chart gets its own scale and the key says so.

To restyle, edit `site/themes/<name>.css` in this app folder: those files hold every color, size, and timing as named tokens, and `site/styles/` holds only the layout. A new theme is a new file there, named in `theme`.
