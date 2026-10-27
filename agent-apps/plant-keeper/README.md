# plant-keeper

## What this makes

A page of the person's houseplants, one card each. Every card has a soil ring that drains over the plant's watering interval, turning amber at 70 % and red on the day it is due. The plant's leaves droop once it is overdue. Tapping "Watered" drops water into the pot, fills the ring, and perks the leaves back up. The header counts the plants thirsty today. Room tabs sort the cards, and a fourteen-day strip shows which plants need water on each day ahead. Each plant also has a sheet with its light, notes, a water log, and a way to log a watering on another day. Settings exports and imports the log.

Before asking for personal details, ask in one message: "What plants do you have, and roughly how often does each get watered? Which room is each in?"

## Run

From the person's project folder:

```sh
cd <project> && python3 <agent-apps root>/plant-keeper/scripts/run.py
```

It reads `plant-keeper.inputs.json` in the project folder. When the person has none yet, copy `inputs.example.json` from this app's folder to `<project>/plant-keeper.inputs.json` first, then run. The page goes to `out/plant-keeper/` in the project folder. A missing or wrong key is named in one line and the run stops with exit code 2.

## Check

Serve `out/plant-keeper/` (see Host) and open `http://localhost:8000/`. Check that:

- There is one card per plant in the inputs, under its room.
- The header's count of thirsty plants matches the cards whose ring has run out.
- The fourteen-day strip shows plant icons on their due days.
- Tapping Watered on a thirsty card fills its ring and lowers the count, and that stays the same after a reload.

`out/plant-keeper/config.js` holds every plant from the inputs.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/plant-keeper
```

Then open `http://localhost:8000/`. Any static host can serve the `out/plant-keeper/` folder as it is, at any path. Waterings and notes are kept in the browser that opened the page, under `plant-keeper:` keys. Export and Import in Settings move them to another device.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens the app's page on code-config.com. It sends no data. Remove the `<script src="./badge.js" defer></script>` line from `index.html` (or from `site/index.html` before a run) to take it away.

## Make it yours

Every change here is an edit to `plant-keeper.inputs.json` and a fresh run. Nothing needs to be installed.

- `name`: the header.
- `plants`: one entry per plant, with `id`, `name`, `type`, `intervalDays`, `light`, and `room`.
  - `id` is short and never changes, because the watering log is kept by it.
  - `type` picks the drawing: `fern`, `succulent`, `vine`, `palm`, `fiddle`, `cactus`, `herb`, or `orchid`. Common names such as monstera, pothos, snake plant, basil, or echeveria pick the nearest drawing, and when `type` names none, the plant's `name` is tried. Anything else gets a neutral leaf with the plant's initial.
  - Optional `wateredDaysAgo` starts the ring partway down on the first visit. Left out, a plant starts with a full ring.
  - Optional `notes` fills the plant's notes.
- `rooms`: the tab order. A room a plant names that is missing from this list is added at the end.
- `theme`: `greenhouse` (white, leaf green rings, terracotta pots), `nightgarden` (deep green black, mint rings, clay pots), or `auto` (greenhouse by day, nightgarden when the device is set to dark).

Colors live in `site/themes/`, one file per theme, as tokens only. The layout lives in `site/styles/` and names no color. The plant drawings are one sprite, `site/assets/plants.svg`. Each droop-able part is a group with the class `lf-l` or `lf-r` and a `transform-origin` at its base.
