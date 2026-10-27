# Tiny Tornado

## What this makes

A sixty-second tornado game in `out/tiny-tornado/`: the person steers a funnel through a little farm town that carries
the name they chose, lifts fences, cows, cars, and barns as the funnel grows, and gets a damage report at the end.

## Run

From the person's project folder:

```
cd <project> && python3 <agent-apps folder>/tiny-tornado/scripts/run.py
```

It reads `tiny-tornado.inputs.json` from that folder, or this app's `inputs.example.json` when the folder has none
yet, and writes the game to `out/tiny-tornado/`. Run it again after any change to the inputs; each run replaces the
folder.

## Check

- `out/tiny-tornado/index.html`, `out/tiny-tornado/config.js`, and `out/tiny-tornado/theme.css` exist.
- `config.js` holds the person's `townName` and `playerName`.
- Served and opened in a browser, the title card shows the town's name over a live storm already tearing through the
  town, and the water tower carries the same name.

## Host

The game is a folder of plain files and has to be served, not opened as a file:

```
cd <project> && python3 -m http.server 8000 --directory out/tiny-tornado
```

then open `http://localhost:8000/`. To keep it online, copy the `out/tiny-tornado/` folder as it is to any static
host the person names.

## Make it yours

Ask for the personal things in one message: "What's your name, what's the town called, and which look (plains, dusk,
or snow)?" Then copy `inputs.example.json` to `<project>/tiny-tornado.inputs.json`, fill it in, and run again.

- `playerName`: the person's name, on the damage report. Ask for it.
- `townName`: the town's name, on the title card and the water tower, up to 24 letters. Ask for it.
- `theme`: `plains`, `dusk`, or `snow`. Ask for it.
- `title`: the name on the title card; default `Tiny Tornado`.
- `seed`: any word; the same word builds the same town. Defaults to the town's name.
- `runSeconds`: how long the storm lasts, 15 to 600; default 60.

Each look is one file in `site/themes/` holding colors and a few numbers for the sky, ground, props, funnel, and
interface, with a light and a dark scheme that follow the device's setting.
