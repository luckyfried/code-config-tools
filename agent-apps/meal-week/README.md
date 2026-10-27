# Meal Week

## What this makes

A page for one week of meals, `out/meal-week/`, that opens in any browser. Breakfast, lunch, and dinner for seven days sit on one board of tiles: each tile has its cuisine's color down the left edge, a small arc in the corner that fills with the minutes the meal takes (a full ring is an hour), and the meal's name in a serif. Tap a tile for its ingredients and amounts. A slot with no meal is a dashed tile that names the slot.

Beside the week is the grocery list those meals need. Every ingredient is merged by name; amounts in the same unit are added up, and a second unit gets its own line under the same name (10 cloves and 1 head of garlic). The list follows the store's aisle order and leaves off the pantry. Shop mode shows the list with big checkboxes: a check draws its stroke, strikes the line, and the aisle's count ticks down. What is checked stays checked across screens and reloads, kept in the browser under `meal-week`, one set per week.

The week picker steps between the plan's weeks and the board slides sideways to the next one. Print makes two pages on Letter or A4: the week in landscape with its name in the display serif, then the list in two columns with a square to tick by each item. On a phone the week shows one day per screen with a day strip on top, and List and Shop are their own screens. On a computer the week and the list sit side by side.

On the very first open the page shows itself once: the board deals in, slides to the other week and back, and checks three items and clears them again. Nothing of it is kept, and the first tap or key ends it.

It needs one file in your project, `meal-week.inputs.json`. `inputs.example.json` in this folder is a full example with a note on each key:

- `weekOf`: the Monday the week starts on, `YYYY-MM-DD`.
- `name`: optional title; left out, the page says "Week of October 26".
- `people`: how many the amounts are for.
- `slots`: the meals of each day, in order (`breakfast`, `lunch`, `dinner` by default).
- `days`: seven days, `mon` to `sun`, each `{ day, meals }`. `meals` maps a slot to `{ name, cuisine, minutes, ingredients }`, and each ingredient is `{ amount, unit, name, aisle }` (`unit` is `""` for a count). A slot left out is an open tile.
- `aisles`: the list's sections in the order the person walks the store.
- `pantry`: ingredient names that never go on the list.
- `otherWeeks`: optional weeks for the picker, each `{ weekOf, name, days }`.
- `theme`: `market` (chalk white, graphite type), `bistro` (slate, bone type, italic meal names), or `auto` (market by day, bistro when the device is in dark mode).

Ask the person, in one message: "How many people am I cooking for? Anything to avoid? A few meals you love, so I can build the week around them? What's already in the pantry?" Then plan the week around their answers, with an aisle for every ingredient.

## Run

```sh
cd <project> && python3 <this folder>/scripts/run.py
```

It reads `meal-week.inputs.json`, checks every key, and writes `out/meal-week/`: the page, `config.js` with the plan, and `theme.css` with the chosen theme. It prints how many items the week needs from the store, which is the number the list shows. A missing or wrong key is named in one line each and nothing is written. Running it again on the same inputs writes the same files. It needs Python 3.12 or newer and nothing else.

## Check

1. `out/meal-week/config.js` holds the person's week, seven days.
2. Serve the page (see Host) and open it. Every filled slot is a tile with its edge color and its arc; an open slot is a dashed tile that names it.
3. The list's count ("69 of 69 to buy") matches the number `run.py` printed.
4. Open Shop and check an item: the box draws its check, the line strikes, and the aisle count drops by one. Switch to Week and back, then reload: it is still checked.
5. Press the left arrow button: the board slides to the earlier week.
6. Print, or save as PDF: two pages, the week in landscape, then the list in two columns.
7. The browser console shows no errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/meal-week
```

Then open http://localhost:8000/. The folder is plain files with its fonts inside it, so any static host serves it as it is and nothing is fetched from elsewhere.

## Make it yours

Everything here needs only a new run of `run.py`; there is no build step.

- Every key in `meal-week.inputs.json`: the week, its meals and ingredients, the people, the slots, the aisle order, the pantry, other weeks, and the theme.
- A theme: copy `site/themes/market.css` to a new file in `site/themes/`, change its colors, and set `theme` to the file's name. Every color on the page comes from those variables, the ten cuisine edges (`--edge-1` to `--edge-10`) and the printed pages included.
- Which edge color a cuisine takes: the table at the top of `site/js/plan.js`. Within one week no two cuisines share a color: a cuisine whose color is already taken that week takes the next free one, and a cuisine the table does not list starts from a color picked by its letters.
- The page itself: `site/index.html`, the styles in `site/styles/` (`week.css` for the board and tiles, `list.css` for the list, shop, and meal sheet, `print.css` for the two printed pages), and the code in `site/js/`.
