# Countdown Wall

## What this makes

A web page of everything the person is counting down to. The nearest event fills the top with days, hours, minutes,
and seconds on split-flap tiles, over a slow wash of the event's color. The rest are tiles by date with a thin
progress bar, and past events count up as "since" tiles. Any event opens full screen on its own, with its picture
behind it.

## Run

Before asking the person anything, run it from their project folder:

```sh
cd <project> && python3 <agent-apps root>/countdown-wall/scripts/run.py
```

It reads `countdown-wall.inputs.json` from the project folder. When the person has none yet, copy
`inputs.example.json` from this app's folder to `<project>/countdown-wall.inputs.json` first; it holds a sample year
of events and renders with no network. The page is written to `<project>/out/countdown-wall/`.

Then ask, in one message: "What are you counting down to, with dates and times? Pick a color for each, or let me.
Any images to put behind them?" Write the answers into the `events` list (the `_notes` in `inputs.example.json`
say what every key means), set `start` on a new event to the day it was added so its progress bar starts there,
put any picture beside the inputs file and name it in `image`, and run the line again.

A key that is missing or wrong is named in one plain line and the run stops with exit code 2; nothing is written
until every line is fixed.

## Check

The run prints `Wrote out/countdown-wall/ (<n> files). Serve it: …`. Serve the folder as Host says and open it:

- the top of the page shows the nearest event that has not happened yet, and its seconds flap over once a second;
- every other future event has one tile, in date order, large and in full color when it is within thirty days;
- every past event has one "since" tile at the bottom, and the Since tab lists them with running counters;
- "Full screen" on the top countdown, or a tap on any tile, shows that one event alone; Escape or the close button
  goes back;
- `out/countdown-wall/data.js` lists every event with its color filled in.

## Host

The page is a folder of static files and must be served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/countdown-wall
```

and open `http://localhost:8000/`. Any static host serves `out/countdown-wall/` as it is, at any path. The page keeps
counting with nothing running behind it; the countdown only needs the run again when events change.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens
this app's page on code-config.com. It sends no data anywhere. To remove it, delete the
`<script src="./badge.js" defer></script>` line from `out/countdown-wall/index.html` (or from `site/index.html` in
this app's folder, so every run leaves it out).

## Make it yours

Everything here changes without Node or a build step.

- **Events**: add, remove, or edit entries in `events`, then run again. `date` takes a date and time
  (`2026-11-13T07:40`, local time) or a date alone for an all-day event that lasts until 23:59. `repeat: "yearly"`
  makes a birthday or holiday roll over to next year instead of turning into a since tile.
- **Colors and icons**: `color` takes a hex color or one of the named colors in the notes; `icon` takes one of the
  icon names in the notes. Left out, colors are given in turn.
- **Theme**: `"theme"` is `celebration` (black, full-color tiles, a glow under the top countdown), `calm` (bone
  paper, soft tints, no glow), or `auto` (calm on a light device, celebration on a dark one). A new look is a new
  file in `site/themes/` with the same token names; name it in `theme`.
- **Words**: `title` sets the name at the top; `hourFormat` is `12` or `24`.
- **Layout and motion**: `site/styles/` holds the layout and the flap; durations live in `site/styles/tokens.css`.
  The page's code is plain JavaScript in `site/js/`.
