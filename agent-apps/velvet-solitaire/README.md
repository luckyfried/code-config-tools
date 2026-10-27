# Velvet Solitaire

## What this makes

A one-page Klondike solitaire the person hosts on their own site: a lit felt table with cloth sheen and a lacquered wood rail, thick glossy cards that tilt as they are dragged and settle with a snap, draw one or three, standard or Vegas scoring (the deck costs $52 and pays $5 a card to the foundations, and the bank carries from game to game), unlimited undo in standard scoring, hints, auto-finish, a clock and move count, and the win cascade. It plays with touch, mouse, and keyboard, and a half-played game stays on the device until the player comes back. With no game in progress, the house plays a hand on the table until the visitor taps to deal in.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/velvet-solitaire/scripts/run.py
```

It reads `velvet-solitaire.inputs.json` in the project folder. When the person has none yet, copy `inputs.example.json` from this app folder to `<project>/velvet-solitaire.inputs.json` first and run it as is; the sample needs no network. The page is written to `<project>/out/velvet-solitaire/`.

Then ask in one message: the title for the page, the name to show on the stats card, draw one or three, standard or Vegas scoring, which table (velvet green, midnight blue, or ivory club), and whether they want their initials or a picture of their own on the card backs. Put the answers in the inputs file and run the same line again. A missing or wrong key stops the run with one plain line naming it.

## Check

`out/velvet-solitaire/` holds `index.html`, `config.js`, and `theme.css`. `config.js` carries the inputs' `title` and `scoring`, and `theme.css` is the same bytes as the chosen file in `site/themes/`. Served (see Host), the page shows a dealt table within a second with the house playing a hand; tapping the table deals the player in, and tapping the stock turns a card. `test/rules.html` on the served page lists the rules' fixed cases, and every line reads Pass (the same file runs with `node site/test/rules-test.js` from this folder).

## Host

The output is a static folder. Serve it, never open it as a file, because browsers refuse its modules from a file address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/velvet-solitaire
```

and open `http://localhost:8000/`. To keep it running after the session, upload the contents of `out/velvet-solitaire/` to any static host (GitHub Pages, Netlify, Cloudflare Pages, or the person's own server); it works from a subfolder too. The page calls nothing outside its own folder. Games, stats, and the Vegas bank are kept in the visitor's browser on that device.

## Make it yours

Every key in `velvet-solitaire.inputs.json` (`inputs.example.json` explains each one under `_notes`):

- `title`: the name on the tab, the rail, and the felt's printed seal.
- `playerName`: shown on the stats card; its initials go on a monogram card back.
- `draw`: `1` or `3`.
- `scoring`: `"standard"` or `"vegas"`.
- `theme`: `"velvet-green"`, `"midnight-blue"`, or `"ivory-club"`. Each has a day and a night look that follows the visitor's light or dark setting.
- `cardBack`: `"classic"`, `"lattice"`, `"monogram"`, or the path to a picture beside the inputs file (PNG, JPEG, WebP, or GIF); the run copies it into the output's `media/` folder.
- `sound`: `true` or `false`.

Visitors can change draw, scoring, table, light, and sound from the menu; their choices stay on their device.

Beyond the inputs: a theme is one file of CSS custom properties in `site/themes/` (felt, sheen, rail wood, lights, card inks, card backs, and the page's colors), so a new table is a copied file with new values. The card faces are drawn in `site/faces.js`, the felt, rail, and lights in `site/scene/table.js`, the card material in `site/scene/card.js`, and the rules in `site/game/rules.js`. The four sounds and the studio light map are written by `scripts/make_sounds.py` and `scripts/make_env.py`, standard-library Python; run either again after changing it. Nothing here needs a build step or Node.
