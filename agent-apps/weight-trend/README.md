# Weight Trend

## What this makes

A daily weigh-in page at `out/weight-trend/index.html`. Each morning a scale dial opens on yesterday's trend, so logging today's weight takes a tap or two on plus and minus, a turn or a flick of the dial, or the arrow keys, then Log weigh-in or Enter. The chart draws every weigh-in as a faint dot and the trend through them as one smooth line, a moving average that washes out water and salt, with the goal as a dashed line and a marker on the day the trend reaches it at its current pace. A chip shows the trend's change over the last seven days, and says Holding when it is flat. The Chart screen shows 90 days, a year, or every weigh-in, with a list where any weigh-in can be deleted. Settings switches kilograms and pounds, changes the goal, and exports or imports the weigh-ins as a file. Everything is saved in the browser. The page opens by drawing the trend to today, then running the forecast on to the goal. Looks: mist (oat paper, a persimmon trend, a plum goal), slate (warm charcoal, an ember trend, a lilac goal), and auto, which follows the system.

## Run

Ask the person: "Kilograms or pounds? What's your goal weight? Do you want the projected date shown on the chart?" Ask their name for the greeting too.

Write their answers into `weight-trend.inputs.json` in their project folder, starting from `inputs.example.json` in this app (it lists every key, with a note on each under `_notes`). Leave out `sample`, which fills a first visit with three made-up months. Then run:

```
cd <project> && python3 <agent-apps root>/weight-trend/scripts/run.py
```

It writes `out/weight-trend/` and prints how to serve it. Running it again gives the same result. If a key is missing or wrong it prints one plain line per problem and stops.

## Check

- `out/weight-trend/index.html`, `config.js`, `theme.css`, and `themes/` exist.
- `config.js` contains the person's `units` and `goal`.
- Serve it, open it, and log a weigh-in: the button turns to Logged today and a dot and the trend line appear on the chart. Reload the page and the weigh-in is still there.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/weight-trend
```

Open http://localhost:8000/. `out/weight-trend/` is a static folder with every file it needs inside it, the font included, and nothing is fetched from anywhere else, so it goes on any static host as it is. Weigh-ins are kept in the browser that opened the page, under the address it was opened at; Export in Settings saves them to a file.

## Make it yours

- Change the look with `theme`, then run again.
- Set `smoothing` between 0.01 and 0.5 to make the trend calmer or quicker to follow the scale; 0.1 is the usual.
- Set `showProjection` to false to hide the goal date and its marker.
