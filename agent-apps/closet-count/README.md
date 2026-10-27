# Closet Count

## What this makes

A wardrobe page of the clothes a person actually wears. It opens with the whole closet sliding into a strip of paint
chips sorted by hue, every chip starting where its piece sits in the closet and finding its place in the color order;
then the closet settles below it by kind, each piece a silhouette tinted with its own color and labeled with what it
now costs per wear.

Today holds the outfit rack: a card per outfit, flat-laid (top, bottom, shoes, layer), snapping to center as it is
flicked, with each layer drifting at its own rate as the card passes. Under the rack, every piece of the outfit in
front sits in a thirty-wears ring with its cost per wear. "Wear this today" marks the outfit and its pieces; "Wear"
under a ring marks one piece. The cost per wear rolls down in tabular figures and the ring fills, closing with an
overshoot at thirty. On a laptop the arrow keys flick the rack and W wears the outfit in front.

A piece unworn for `dustyDays` (90 by default) fades over the following six weeks and gathers on the Dusty shelf,
with Keep (its clock starts again) and Give away (it leaves the closet, its outfits, and the capsule). The capsule
shows the season's chosen pieces as a tight grid under the count, set in Fraunces. The closet filters by season and
color, Add item and New outfit (one select per slot) grow it, and Settings holds the currency, Export, Import, and
Start over.

Everything the person taps or adds stays in the browser's localStorage under `closet-count`. The starting closet
comes from `closet-count.inputs.json` in the project; a later run adds new items and outfits to a browser that has
already opened the page and leaves its taps alone. Export writes `closet-count.json`, the file to read for a season
look-back or a give-away list. `inputs.example.json` is a full sample (Sam's closet: 36 pieces, six outfits) and its
`_notes` object explains every key.

## Run

```sh
cd <project> && python3 <agent-apps>/closet-count/scripts/run.py
```

`<project>` is the folder that holds `closet-count.inputs.json`; `<agent-apps>` is the folder this app sits in. The run
copies the page into `<project>/out/closet-count/` and writes `config.js` (the closet) and `theme.css` beside it.
Running it again on the same file gives the same output.

To start, ask in one message: "What currency? Walk me through what's in your closet that you actually wear: each item
with its color and roughly what it cost (skip anything you don't know). Light or dark?" Write each piece into `items`
with an `id`, a `name`, a `category`, and a hex `color`; add `price`, `brand`, `seasons`, `wears`, and `lastWorn` when
the person says them. Stack a few `outfits` from what they describe wearing together, then run.

## Check

- The run prints `Wrote out/closet-count/ (<n> files).` and exits 0. A problem in the inputs file prints one plain
  line per problem, names the key, and exits 2.
- Served, `config.js` carries every item, the closet shows one swatch per item, and the strip carries
  `data-hue-sorted="true"`.
- Building an outfit with one piece per slot adds a card to the rack.
- "Wear" under a ring raises that piece's `data-wears` by one and lowers its `data-cpw` to price ÷ wears, and a
  reload keeps it.
- A piece whose `lastWorn` is older than `dustyDays` sits on the Dusty shelf.
- Export, then Import of the same file, gives back the same closet. The page logs no console errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/closet-count
```

Then open `http://localhost:8000/`. The folder `out/closet-count/` is the whole page: any static host serves it as it
is, at any path. It needs no network once it loads.

## Make it yours

Without Node, by editing `closet-count.inputs.json` and running `run.py` again:

- every key in the file: `name` (the title), `currency` (an ISO code), `items`, `outfits`, `slots` (the outfit slots
  in order; `top` also takes a dress), `dustyDays`, and `capsuleSize`;
- `theme`: `auto` (light or dark from the device), `boutique` (light: bone paper, warm-gray outlines, the ring in
  brass), or `atelier` (dark: charcoal, swatches at full chroma, the ring in bone). A new look is a new file in
  `src/themes/`, copied from one there; its file name becomes a `theme` value with no rebuild;
- `copy`: any word on the page by its key, such as `"rack.markWorn": "Wearing it"`. `dist/copy.js` lists every key
  and its word; leave a key out to keep its word.

With Node, for a new component, a new slot shape, a change to a page, or a new dependency: edit `src/`, then from
this folder run

```sh
npm ci && npm run build && rm -rf node_modules
```

`dist/` is the built page that `run.py` copies; commit it with the change. `node_modules/` never stays in the folder.
