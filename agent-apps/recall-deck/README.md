# Recall Deck

## What this makes

A flashcard deck with spaced repetition in one web page, built into `out/recall-deck/` in your project. The Study screen deals today's cards from a stack of three: type the answer, and the card tilts and turns in 3D to show the right one, with every letter you missed or added marked in the theme's warning color. Swipe the card right if you knew it or left to see it again (or press 1 to 4 on a computer), and the next card rises from the stack while the 30-day forecast re-tallies with its bars easing to their new heights. Each card is scheduled with SM-2 (the E-Factor and the 1, 6, then I × EF intervals). Browse searches, filters by tag, and sorts every card; Forecast shows the next 30 days, a half year of days studied as a heat strip, and your recall. Progress stays in the browser under `recall-deck:progress`, with Export and Import in Settings.

Ask the person, in one message: "What do you want to remember? Paste the cards, or tell me the topic and I will write them. How many new cards a day, and do you want to type each answer?" Then copy `inputs.example.json` from this folder to `recall-deck.inputs.json` in the project folder and set `deckName`, `cards`, `newPerDay`, `typing`, `font` (`sans` or `serif`), and `theme` (`index-card`, `blackboard`, or `auto`). `progress` is optional: the deck's starting schedule, in the format Export writes; delete it for a fresh deck. `_notes` explains every key.

## Run

```
cd <project> && python3 <app>/scripts/run.py
```

It checks `recall-deck.inputs.json`, names any key that is missing or wrong in one line each, and writes `out/recall-deck/`. Running it again gives the same files.

## Check

`out/recall-deck/index.html`, `config.js`, and `theme.css` exist, and `config.js` carries `deckName` and every card. Serve the folder (below) and open it: the header shows `deckName`, Browse lists every card, and its tag chips list every tag. The first open walks through the deck once on its own: a typed answer with one letter off, the card turning, the diff on its back, a swipe right as the forecast re-tallies, then the next card turning and swiped left to come back again. Answer two cards and reload: the header's "done" count and the forecast are the same as before the reload.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/recall-deck
```

Then open http://localhost:8000/. The folder is static, so any file host serves it from any path.

## Make it yours

No Node needed: every input key, the theme, and the copy. Change `recall-deck.inputs.json` and run `run.py` again. A theme is a file in `src/themes/` (`index-card.css`, `blackboard.css`, `auto.css`); copy one, change its colors, and name it in `theme`. A card's `id` keeps its progress, so a rerun with new cards keeps every card that is still there.

Needs Node: a component, a page, or a dependency. Edit `src/`, then in this folder run:

```
npm ci
npm run build
rm -rf node_modules
```

`npm test` runs the scheduler's tests.
