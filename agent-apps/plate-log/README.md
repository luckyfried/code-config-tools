# Plate Log

## What this makes

A food diary page, `out/plate-log/`, that opens in any browser. Three rings, one each for protein, carbs, and fat, fill inside a calorie arc as you log food. Your usual foods sit in a tray of large tiles, ordered by the time of day. The Week view shows seven small rings, your daily averages, and how many days in a row you landed on target. Settings changes targets and exports or imports the log as a file. The log stays in the browser it was made in.

It needs one file in your project, `plate-log.inputs.json`. `inputs.example.json` in this folder shows every key with a note on each:

- `name`: the name the greeting uses.
- `targets`: daily `calories`, `protein`, `carbs`, and `fat`.
- `foods`: the ten to twenty foods the person eats most weeks, each with an `id`, a `name`, a `serving` in words, and the numbers for one serving. `usual` (breakfast, lunch, dinner, or snack) puts a food first in the tray at that time of day.
- `meals`: the meal names in the order the day runs.
- `water`: true adds a counter of glasses of water.
- `theme`: `fresh` (white), `kitchen` (charcoal), or `auto` (fresh by day, kitchen when the device is set to dark).
- `startLog`: optional meals a browser shows before it has a log of its own, counted back from today. Leave it out for a clean start.

Ask the person: "What daily calories, protein, carbs, and fat are you aiming for? List the ten to twenty foods you eat most weeks (I'll fill in the numbers for a usual serving and you can correct them). Do you want a water counter?" Fill in the numbers for each food from what a usual serving holds, show them, and take their corrections.

## Run

```sh
cd <project> && python3 <this folder>/scripts/run.py
```

It reads `plate-log.inputs.json`, checks every key, and writes `out/plate-log/`: the built page, `config.js` with the inputs, and `theme.css` with the chosen theme. A missing or wrong key is named in one line and nothing is written. Running it again on the same inputs writes the same files.

## Check

1. `out/plate-log/config.js` holds the person's targets and foods.
2. Serve the page (see Host) and open it. Tap a food in the tray, then Add: the rings move, one pulses, and the food appears under its meal.
3. Reload the page: the food is still logged.
4. Open Week: seven days, each with its small rings.
5. Log enough of one macro to pass its target: the ring keeps going as a second lap in a deeper shade.
6. In Settings, Export, then Import the same file: the log comes back as it was.
7. The browser console shows no errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/plate-log
```

Then open http://localhost:8000/. The folder is plain files, so any static host serves it as it is.

## Make it yours

These need no Node, only a new run of `run.py`:

- Every key in `plate-log.inputs.json`: name, targets, foods, meals, water, theme, and the starting log.
- A theme: copy `src/themes/fresh.css` to a new file in `src/themes/`, change its colors, and set `theme` to the file's name. Every color in the page, the ring colors included, comes from those variables.
- Copy that comes from the inputs, such as the food names and servings and the meal names.

These change the page itself and need Node 20 or newer. Edit `src/`, then run the three commands from this folder:

```sh
npm ci && npm run build && rm -rf node_modules
```

- A component, such as the rings (`src/components/Rings.tsx`) or the tray (`src/components/QuickTray.tsx`).
- A page, such as Week (`src/components/WeekPanel.tsx`) or Settings (`src/components/SettingsPanel.tsx`).
- A dependency: add it with `npm install <name>` before the build.

The build writes `dist/`, which `run.py` copies into `out/plate-log/`.
