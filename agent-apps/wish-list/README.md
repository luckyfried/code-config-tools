# Wish List

## What this makes

A wish list page for a birthday, a holiday, a baby, or a move, to send to the people who ask "what do you want?"

It opens on a paper-cut scene in the theme's colors: gift boxes, ribbons, and hanging tags in layers that drift with
the pointer, or with the phone as it tilts, and sink away as a phone scrolls. Under it the cards deal out of the gift
pile, one per wish: the picture standing on a soft plinth, the name, the size and color notes, the price, and the
store it comes from. Cards tilt toward the pointer with a glossy sheen. A picture opens full size with a tap.

The bar under the scene holds the total still wished for, price filters cut at round amounts near the thirds of the
list, a switch to hide what is already gotten, and Shuffle, which gathers the cards into a fanned hand and deals them
again. Prices and the total roll like a counter whenever a filter changes.

"I'll get this" opens a text or an email to the owner with the gift already named, so two people never buy the same
thing, and marks the card "Yours" on that phone or laptop. When the owner hears, their agent sets `"claimed": true`
on the item and runs again; the card then folds under a gift tag and a "Gotten" stamp lands on it. On a first visit
the page plays once by itself for a few seconds (a filter, back to everything, a shuffle); any touch or key hands it
over. The filter, the switch, the order, and "Yours" marks are kept on each device under the key `wish-list`.

The list lives in `wish-list.inputs.json` in your project. `inputs.example.json` is a full sample (Maya turns 30,
twelve wishes, two already gotten) and its `_notes` object explains every key. Its pictures are in `example/pictures/`.

## Run

```sh
cd <project> && python3 <agent-apps>/wish-list/scripts/run.py
```

`<project>` is the folder that holds `wish-list.inputs.json`; `<agent-apps>` is the folder this app sits in. The run
copies the page into `<project>/out/wish-list/`, copies every item's picture into `out/wish-list/media/`, writes the
list and the theme beside `index.html`, and prints the total still wished for. Running it again on the same file
gives the same output.

To start, ask the person in one message: "Who is the list for, and what's the occasion? What would you love: a name,
a price, and a link for each, plus a picture if you have one? How should friends tell you they're getting something,
a phone number or an email? And ribbon, kraft, or midnight?" Put the pictures in a folder beside the inputs file,
such as `pictures/`, write the file, and run. When the person says someone is getting an item, set `"claimed": true`
on it and run again.

## Check

- The run prints `Still wished for: <amount> across <n> of <m> items.`, which is the sum of the prices without
  `"claimed": true`, then `Wrote out/wish-list/ (<n> files).`, and exits 0. A problem in the inputs file prints one
  plain line per problem, names the key, and exits 2.
- `out/wish-list/media/` holds one picture per item that names one.
- Served, the page shows every item with its price, and the bar's total with "Everything" picked equals the printed
  total.
- A claimed item shows folded under a "Gotten" tag.
- "I'll get this" opens a box whose Text and Email buttons address the owner's phone or email with the item named.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/wish-list
```

Then open `http://localhost:8000/`. The folder `out/wish-list/` is the whole page: any static host serves it as it
is, at any path, and it fetches nothing once it loads.

## Make it yours

Without Node, by editing `wish-list.inputs.json` and running `run.py` again:

- every key in the file: `owner` (`name`, plus `phone`, `email`, or both), `occasion` (the big title), `currency` (a
  three-letter code such as USD or EUR; prices are written the way that currency is), and `items`, each with `name`,
  `price`, and any of `url`, `image`, `note`, `priority` (`high` shows a Most wanted badge), and `claimed`;
- `theme`: `auto` (ribbon by day, midnight by night, following the device), `ribbon` (light: pink tissue and a
  raspberry ribbon), `kraft` (light: brown paper, twine, and forest green), or `midnight` (dark: navy and gold). A new
  look is a new file in `src/themes/`, copied from one there; its file name becomes a `theme` value with no rebuild;
- `copy`: the words on the page by key, such as `"getThis": "Count me in"`. `copy.js` in the built page lists every
  key; leave one out to keep its word.

With Node, for a new card field, a new component, a change to the page, or a new dependency: edit `src/`, then from
this folder run

```sh
npm ci && npm run build && rm -rf node_modules
```

`dist/` is the built page that `run.py` copies; `node_modules/` never stays in the folder.
