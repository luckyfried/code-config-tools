# Recipe Box

## What this makes

A page of recipes you found for the person, laid out as photo cards on a kitchen table: each card has the dish,
its total time drawn as a ring, its servings as tiny plates, and your one line on why you picked it. Along the
bottom runs the week on a wooden strip, seven days. The person keeps a recipe, skips it, or puts it on a day, and
taps Plan the week; on your next turn you read those choices, set the week, and write the shopping list, which
prints up out of the strip like a till receipt, sorted by aisle, with lines they tick off in the store.

Every recipe, choice, and list lives in `<project>/data/recipe-box/`, the project's own data folder, on this
computer. The page's filter and ticked lines are kept in the browser under the one key `recipe-box`.

## Run

```sh
cd <project> && python3 <agent-apps>/recipe-box/scripts/run.py --serve
```

`<project>` is the folder that holds `recipe-box.inputs.json` (copy `inputs.example.json` there to start);
`<agent-apps>` is the folder this app sits in. The run writes the page into `<project>/out/recipe-box/`, then
serves the page and the person's choices at `http://127.0.0.1:8000/` on this computer until stopped (`--port N`
picks another port). Without `--serve` it only writes the page. Running it again on the same inputs gives the
same output.

To start, ask the person in one message: what they love to cook, anything they never eat, how many people they
cook for, and how many dinners a week they want planned. Put the answers in `name`, `ask`, and `household`, and
run.

### The playbook

1. **Add what you find with `--add`.** Write a JSON list of recipes to a file and run
   `cd <project> && python3 <agent-apps>/recipe-box/scripts/run.py --add found.json`. Each recipe carries `id`
   (a short slug), `title`, `image` (an https address of the dish, or `media/<file>` for art in the page),
   `source` (the recipe's link), `color` (the dish's main color, shown while the photo loads), `minutes`,
   `servings`, `ingredients` (each `{name, amount, unit, aisle}`, with `amount` and `unit` null when there is
   none, and `aisle` one of produce, bakery, meat & fish, dairy & eggs, pantry, spices, frozen, or other),
   `steps`, `tags`, `why` (one line on why it suits them), and `agent_notes`. A new recipe lands as `new`. An
   `id` that is already in the box updates that recipe; if the person changed it since you read it, the line
   says `Not changed` and names the revision, so read it again and add your change to the newer one.
2. **Read their choices with `--work`.** When the person says they have chosen, run
   `cd <project> && python3 <agent-apps>/recipe-box/scripts/run.py --work`. It takes every waiting choice once
   and prints one line for each: `Miso Ramen: kept.`, `Black Bean Tacos: on Friday.`, `Blueberry Pancakes:
   skipped.`, and for Plan the week, `Shopping list for the week of 2026-10-19: 29 items from 4 recipes`. The
   page shows each result on its card. Tell the person what the lines say.
3. **Nothing leaves this computer on a choice alone.** Keep, skip, this week, and Plan the week change only the
   records in the data folder. Ordering groceries, booking anything, or sending the list anywhere is a separate
   step you ask the person about in the conversation first.

No one wakes you when a choice lands: the page says the agent checks when asked, and the person asks you.

## Check

- `cd <project> && python3 <agent-apps>/recipe-box/scripts/run.py --check` prints the data folder's health, one
  fact per line, ending `ok: yes`, and exits 0. It exits 1 when something is wrong and the lines say what.
- The run prints `Wrote out/recipe-box/ (<n> files).` and exits 0. A problem in the inputs file prints one plain
  line per problem, names the key, and exits 2.
- Served with `--serve`, the page shows the person's name in the title, every recipe from `--add` as a card, and
  the status line says when you last checked. The same tap twice makes one choice in
  `<project>/data/recipe-box/inbox/`.
- After `--work` takes a Plan the week, `data/recipe-box/` holds a list record whose items add up the week's
  ingredients for the household, and the page opens it as the receipt.

## Host

The page needs `--serve` to take choices: it runs on this computer and stops when the session ends, and the
records stay in `<project>/data/recipe-box/` for the next `--serve`. To show the box without taking choices,
serve the output folder as it is:

```sh
cd <project> && python3 -m http.server 8000 --directory out/recipe-box
```

Then open `http://localhost:8000/`. Served this way, or put on any static host, the page shows the sample recipes,
a sample week, and a sample list, marked "Sample week" at the top, and its buttons take no choices. The page never
shows a command; to make choices on it, serve it with the Run command above. It fetches nothing from outside but the
photos a recipe names.

## Make it yours

Without Node, by editing `recipe-box.inputs.json` and running `run.py` again:

- `name`: whose box it is, in the title.
- `ask`: what they want you to look for, shown under the title so the two of you agree on it.
- `household`: how many people they cook for; the recipe details and the shopping list scale to it.
- `week_start`: `monday` or `sunday`, the first day on the strip.
- `theme`: `kitchen` (light: cream paper, tomato red, and a pale oak strip), `cast-iron` (dark: charcoal, ember
  orange, and a walnut strip), or `auto` (kitchen by day, cast iron by night, following the device). A new look is
  a new file in `src/themes/`, copied from one there; its file name becomes a `theme` value with no rebuild.
- `copy`: the page's words by key, such as `"planWeek": "Plan the week"`. `src/lib/copy.ts` lists every key; a key
  left out keeps its word.
- `sample`: what the page shows when it is not served with `--serve`; `sampleInbox` gives those sample cards their
  choices.

With Node, for a new component, a new screen, a change to how the page works, or a new dependency: edit `src/`,
then from this folder run

```sh
npm ci && npm run build && rm -rf node_modules
```

and run `run.py` again. `dist/` is what `run.py` copies, so it ships in the folder.
