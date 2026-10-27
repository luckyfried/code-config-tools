# Spend Map

## What this makes

A page that draws each month of a bank's CSV export as a flow: income on the left, the person's own categories in
the middle, and the merchants that took the most on the right, with a Months screen that stacks every month by
category and a Categories screen that lists the month's totals.

## Run

From the project folder:

```
cd <project> && python3 <agent-apps folder>/spend-map/scripts/run.py
```

It reads `<project>/spend-map.inputs.json` and writes `<project>/out/spend-map/`. Before the person has their own
inputs file, copy `inputs.example.json` from this folder to `<project>/spend-map.inputs.json` and run the same line:
its `csvFile` names the six-month sample export that ships in `sample/`.

The script prints the first three rows it read, the merchants no rule matched (they show as Other), and each month's
spending and income. Read those lines back to the person before going on: a wrong date format or amount sign shows
there first.

## Check

- `out/spend-map/index.html`, `config.js`, `theme.css`, and `data.js` exist.
- `data.js` holds exactly `months` months, the newest one being the newest month in the export.
- No date from the export appears in `out/spend-map/` (`grep -r "09/29/2026" out/spend-map` finds nothing for the
  sample): the page carries monthly totals only.
- Served, the page opens on the newest month with the map drawn and the month's total at the top.

## Host

Serve the output folder: `cd <project> && python3 -m http.server 8000 --directory out/spend-map`, then open
`http://localhost:8000/`. A static host takes the `out/spend-map` folder as it is. Before putting it online, ask
whether merchant names should show on a public page; when the answer is no, set `showMerchants` to false and run
again, and each category then ends in its merchant count instead of names. For a cloud agent: put the
`out/spend-map` folder online.

## Make it yours

Ask for the personal things in one message: which bank the export is from and where the file is, the categories
they think in, and how many months to show. Then fill `<project>/spend-map.inputs.json`:

- `csvFile`: the export, relative to the inputs file. Put the file beside it.
- `columns`: the header names of the date, description, and amount columns (`date`, `description`, `amount`), and
  `category` when the export has one (Mint, YNAB, and Monarch do).
  With separate debit and credit columns, name them `debit` and `credit` and set `amountSign` to
  `debit-credit-columns`.
- `dateFormat`: the dates' form as Python writes it, such as `%m/%d/%Y` or `%Y-%m-%d`.
- `amountSign`: `negative-is-spend` (most checking exports), `positive-is-spend` (most card exports), or
  `debit-credit-columns`.
- `currency`: a three-letter code; USD when left out.
- `rules`: `{ "match": "TRADER JOE", "category": "groceries", "merchant": "Trader Joe's" }`, first match wins,
  matched anywhere in the description and in any case. `category` is a category id, `income`, or `ignore` (transfers
  between the person's own accounts). `merchant` is the name the map shows; without it, the description is cleaned.
  Read the unmatched merchants run.py prints and add rules for the large ones.
- `categories`: `{ "id": "groceries", "label": "Groceries", "color": "#22A35E" }`, in the order the map stacks them.
- `months`: how many months back to show, ending at the export's newest month. Defaults to 6.
- `showMerchants`: false keeps merchant names off the page. Defaults to true.
- `theme`: `auto` follows the device, `ledger` is the light look, `vault` the dark one. The switch at the top of the
  page flips between them and the page remembers the choice.
