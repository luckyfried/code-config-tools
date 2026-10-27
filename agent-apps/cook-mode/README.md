# Cook Mode

## What this makes

A site of the person's own recipes with a cook mode for the stove: one step per screen in big type, that step's
ingredients pinned below it, and every time in the text ("10 minutes") a chip that starts a timer. It has a servings
slider that rescales every quantity, a wall of recipe cards under a live "Tonight" card, and a shopping list for the
week. The person never fills in a form: you write the recipes from whatever they send.

## Run

Run this from the person's project folder before asking them anything. It uses their `cook-mode.inputs.json` when it
is there; otherwise copy `inputs.example.json` from this app folder to `cook-mode.inputs.json` in the project first,
and the sample recipe book renders:

```sh
cd <project> && python3 <agent-apps root>/cook-mode/scripts/run.py
```

It writes the site to `out/cook-mode/` in the project folder and prints the line that serves it. Python 3 is all it
needs; nothing is installed or downloaded. A missing or wrong key is named in one plain line, and the run stops with
exit code 2 and writes nothing.

Then ask, in one message: "Metric or US measures? Give me three recipes to start: paste them, send a link, or describe
them and I'll write them up. Which one is tonight's?" Write their answers into `cook-mode.inputs.json` (see "Make it
yours") and run the line again.

## Check

Serve the folder (see Host) and open `http://localhost:8000/`. The run worked when:

- the top of the page is the "Tonight" card for the `pinned` recipe, showing its first step in large type with the
  step's ingredients in a strip below it, and below that one card for each recipe in the inputs;
- opening a recipe and pressing Cook shows step one in 36-pixel type on an otherwise empty screen;
- a step that says "10 minutes" shows a chip, and tapping it turns it into a pill that counts down;
- moving the servings slider to double the servings doubles every quantity;
- the browser console shows no errors.

`out/cook-mode/config.js` holds every recipe from the inputs, and `out/cook-mode/theme.css` the chosen theme.

## Host

The site is a folder of static files, so it keeps running wherever the folder is served. Serve it; never open
`index.html` as a file, because browsers refuse its scripts from a file address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/cook-mode
```

and open `http://localhost:8000/`. On a phone on the same Wi-Fi, open `http://<this computer's address>:8000/`. To
keep it up after this session, copy `out/cook-mode/` as it is to any static host (GitHub Pages, Netlify, Cloudflare
Pages, or any web server); it works at any path, including a subfolder.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds on
each visit. A tap on it opens this app's page on code-config.com. It sends no data anywhere. To remove it, delete the
`<script src="./badge.js" defer></script>` line from `out/cook-mode/index.html` (or from `index.html` in this app
folder before a rebuild, so every later run leaves it out).

Which recipes are marked for this week, the ticked ingredients, the chosen servings, and running timers are kept in
the browser on that device (keys starting with `cook-mode:`), never sent anywhere.

## Make it yours

Everything below is an edit to `<project>/cook-mode.inputs.json` followed by the Run line. None of it needs Node.

- `kitchen`: the site's name ("Sam's kitchen").
- `units`: `"metric"` or `"us"`. Quantities and oven temperatures are shown in this system whatever a recipe was
  written in.
- `theme`: `"butcher"` (pink butcher paper with a faint grain, oxblood; light), `"midnight"` (charcoal, brass; dark),
  or `"auto"` (butcher by day, midnight when the device is in dark mode).
- `pinned`: the `id` of tonight's recipe, shown as the live card at the top.
- `tags`: the tag chips on the index, in this order.
- `recipes`: the recipe book. `inputs.example.json` explains every key in its `_notes` and holds nine worked recipes.

When you write a recipe from a link, a photo, or a description:

- Give it an `id` of lowercase letters, digits, and hyphens, a `title`, `servings` (a whole number), `minutes` (total
  time), a `cuisine` (it also picks the card's edge color), and `tags` from the `tags` list.
- Structure every ingredient so it scales: `amount` as a number (`0.5`, not "½"; `null` for "to taste"), `unit`
  (`g`, `kg`, `ml`, `l`, `tsp`, `tbsp`, `cup`, `oz`, `lb`, `fl oz`, a word such as `bunch`, or `""` for counted
  things), and `name` with any prep after a comma ("onions, finely chopped"; plural for counted things, since one is
  made singular on its own). Never put a quantity inside `name`: free text does not scale.
- Set `step` on each ingredient to the step number (from 1) where it goes in; cook mode pins it to that step's strip.
- Write one action per step, short enough to read across a kitchen. Write every time with a number ("20 minutes",
  "1½ hours", "25-30 minutes"); that is what becomes a timer chip, and "a minute" or "minced" never does. Write oven
  temperatures as `200°C` or `400°F` so they convert.
- `image` is optional: a photo's path relative to the inputs file; the run copies it into `out/cook-mode/media/`.

Changes that need Node (version 20 or later): a new field on a recipe card, a new screen, a different component, or
a new dependency. Edit `src/`, then from this app folder run `npm ci && npm run build`, keep the rebuilt `dist/` and
`package-lock.json` with the app, and delete `node_modules/` before saving the app. A new theme is a file in
`src/themes/` with the same variables as `butcher.css`; name it in `theme` and the run picks it up with no rebuild
(`public/theme.css` is only the default copy built into `dist/`).
