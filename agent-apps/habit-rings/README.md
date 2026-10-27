# Habit Rings

## What this makes

A habit tracker page for one person: three to eight habits as rings on one dial for today, closed with one tap, a streak of days with every ring closed as the headline, and a 53-week year map per habit. It runs on a phone every day and shows the whole year on a desktop. The page is written into `out/habit-rings/` in the project folder.

## Run

From the project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/habit-rings/scripts/run.py
```

It reads `habit-rings.inputs.json` from the project folder. When the person has none yet, copy `inputs.example.json` from this app's folder to `<project>/habit-rings.inputs.json` first and run it as it is: the example shows five habits over a made-up sample year. The run writes `out/habit-rings/` and prints the line to serve it. A missing or wrong key is named in one plain line and the run stops with exit code 2.

Then ask, in one message: "Which three to eight habits do you want to track, one or two words each? Does your week start Monday or Sunday? Light, dark, or follow your system?" Put the answers in the inputs file (see Make it yours), set `"sample": false` so their year starts empty, and run the same line again.

## Check

Serve the folder (below) and open `http://localhost:8000/`. The page shows the greeting with the person's name, the streak number, a dial with one ring per habit (the first five; any more sit as chips with their own small ring), a chip for every habit, and a year map per habit. `out/habit-rings/config.js` carries every habit id from the inputs. Tap a chip, reload, and the ring stays closed. In Settings, Save a copy writes `habit-rings.json`, and Load a copy brings it back.

## Host

The page must be served, not opened as a file, because the browser refuses its modules from a `file://` address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/habit-rings
```

Then open `http://localhost:8000/`. Any static host serves the `out/habit-rings/` folder as it is, at any address or subpath. The person's days stay in the browser that opened the page, under `habit-rings:v1`; nothing is sent anywhere. To move them to another browser or to the page at a new address, use Save a copy there and Load a copy here. When asked to sum up a month, read the `habit-rings.json` the person saved.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com. It sends no data, and it can be removed by removing its script line from `out/habit-rings/index.html` (or from `site/index.html` in this app's folder, so every later run leaves it out).

## Make it yours

Everything below changes with the inputs file and a new run; nothing needs to be built.

- `name`: the greeting, as in "Good morning, Sam".
- `habits`: one to eight, in ring order from the outside in. Each has an `id` (keep it once days are recorded, since the days store it), a `label`, and an `icon` from the list in `inputs.example.json`'s notes. `"target": 8` makes a countable habit whose ring fills one step per tap. `"color": "#22aa66"` replaces the theme's ring color; its five-step year ramp is worked out by `run.py`.
- `weekStart`: `"mon"` or `"sun"`, the first row of every year map.
- `theme`: `"auto"` (paper by day, ink when the device is dark), `"paper"`, `"ink"`, or `"neon"`. The page's Settings can change the week start and the theme on each device too.
- `nudgeHour`: past this hour, with rings still open, the headline says so.
- `sample`: `true` shows the made-up year until it is cleared in Settings; `false` starts empty.

A new look is a new file in `site/themes/`: copy `ink.css` or `paper.css`, change the tokens (`--ring-1` to `--ring-8` are the ring colors), and name it in `theme`. Structure lives in `site/styles/` and names no color; the page's code is in `site/app/`.
