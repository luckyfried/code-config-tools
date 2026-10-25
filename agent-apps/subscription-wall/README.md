# Subscription Wall

## What this makes

A page at `out/subscription-wall/` with every recurring charge on one wall: one colored tile per subscription with its
yearly cost as the big figure, the most expensive one as the hero, the yearly total on top with the twelve months
ahead beside it (a dot per charge, the heaviest month lifted), a Calendar screen, and a By category screen. Each tile
has a "What if I cancel?" toggle that grays the tile and counts the total down to what it would be without it.

## Run

```sh
cd <project> && python3 <agent-apps root>/subscription-wall/scripts/run.py
```

It reads `<project>/subscription-wall.inputs.json` and writes `<project>/out/subscription-wall/`. A charge date that
has passed is moved forward by its period, so the page always shows the next charge. Running it again on the same
inputs on the same day writes the same files. A missing or wrong key stops the run with one line naming it.

## Check

- `out/subscription-wall/data.js` lists every subscription in the inputs, and every `nextCharge` in it is today or
  later.
- `out/subscription-wall/index.html` carries `data-yearly="<total>"` on the headline, and the total is the sum of
  every charge over a year (weekly times 52, monthly times 12, yearly once).
- Served, the wall shows one tile per subscription and the headline shows the same total; on a phone the wall is two
  columns.

## Host

Serve the folder and open it in a browser:

```sh
cd <project> && python3 -m http.server 8000 --directory out/subscription-wall
```

then open `http://localhost:8000/`. Any static host takes `out/subscription-wall/` as it is. On a cloud agent such as
Muse or Dot, put it online: the output folder is `out/subscription-wall/`.

## Make it yours

Write `<project>/subscription-wall.inputs.json`; `inputs.example.json` in this folder shows every key.

- `currency`: the three-letter code every amount is in, such as `USD`, `EUR`, or `GBP`.
- `subscriptions`: one entry per recurring charge, each with `name`, `amount` (the price per charge), `every`
  (`week`, `month`, or `year`), `nextCharge` (`YYYY-MM-DD`; when the person does not know it, use the date it last
  charged and the run moves it forward), `category` (one of `categories`), and optionally `color`, a `#rrggbb` brand
  color whose hue the tile keeps.
- `categories`: the names the By category screen shows.
- `sort`: `cost` (largest yearly cost first) or `renewal` (next charge first); the page can switch it too.
- `theme`: `billboard` (a black wall with saturated tiles), `receipt` (paper with pale tiles and hairline borders),
  or `auto` (receipt in a light system setting, billboard in a dark one). Default to `auto`.

Ask in one message: "What currency? List your subscriptions as name, price, monthly or yearly, and the next charge date
if you know it. Dark or light?" If the person has a bank or card export, draft the list from its repeating charges
and show it to them before running. When they add, cancel, or change one, edit the inputs file and run again.

To restyle, edit a file in `site/themes/` (colors only) or add a new one and name it in `theme`; layout lives in
`site/styles/`. The page is plain HTML, CSS, and JavaScript, so nothing needs building.
