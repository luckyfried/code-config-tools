# Week Board

## What this makes

A weekly task board in one web page, built into `out/week-board/` in your project. Each day of this week is a column (seven days, or Monday to Friday), with a Later rail for things that have no day yet. Drag a card between days: it lifts with a tilt and a deeper shadow, the column it passes opens a slot, and it snaps in when you let go. Check a card and a line draws through it before it folds into that day's done list. Today's column has a thin accent outline and a now marker that moves down it through the day. Anything still open on a past day flies out of that day into today the next time you open the board, one card after another, with a "from Mon" badge on each and a count at the top that ticks up as they land. On a wide screen today takes twice the room of the other days, with the hours of the day marked beside the now marker, and past days fold into slim rails. On a board's very first open one extra card shows how it all moves: it lifts, travels to tomorrow while a slot opens for it, drops in, checks itself off, and folds away; it is never saved, and the first touch or key ends it.

Add (the N key, or the round button on a phone) takes one line and reads a day word at the end: `call the bank fri`, `pay rent tomorrow`, `repaint the fence later`. The words are today, tomorrow, later, and mon to sun (full names too), and the day it found shows as a chip before you add. Tap a card to edit its words, write notes, move it to another day, or delete it. Settings sets the first day of the week, five or seven columns, and the Later rail, and exports or imports every card as a file. Cards stay in the browser under `week-board:board`.

On a phone the board shows one day per screen; swipe between days or tap the day strip on top, and hold a card for a moment to pick it up (drag it to the screen's edge to reach the next day). On a computer the arrow keys move between cards, Shift with an arrow moves the focused card to the next day or up and down its list, X checks it, and Enter opens it.

Ask the person, in one message: "Seven days or just workdays? What are five to ten things on your plate this week, and which day for each? Graphite, linen, or forest?" Then copy `inputs.example.json` from this folder to `week-board.inputs.json` in the project folder and set `columns`, `weekStart`, `later`, `seedTasks`, `name`, and `theme` (`graphite`, `linen`, `forest`, or `auto`). `_notes` explains every key. The seed tasks fill the board on its first open; after that the board is the person's, and Settings holds the columns and week start.

## Run

```
cd <project> && python3 <app>/scripts/run.py
```

It checks `week-board.inputs.json`, names any key that is missing or wrong in one line each, and writes `out/week-board/`. Running it again gives the same files.

## Check

Serve the folder (below) and open it. The title is `name`, the board shows `columns` days starting on `weekStart`, and every seed task sits on its day. Drag a card from one day to another and reload: it stays where you put it. Open the page with `?today=` and a later date this week, such as `http://localhost:8000/?today=2026-10-23`: open cards from the days before slide into that day with a "from" badge and the count at the top. In a phone-sized window the page shows one day with the day strip above it.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/week-board
```

Then open http://localhost:8000/. The folder is static, so any file host serves it from any path.

## Make it yours

No Node needed: every input key, the theme, and the copy. Change `week-board.inputs.json` and run `run.py` again. A theme is a file in `src/themes/` (`graphite.css`, `linen.css`, `forest.css`, `auto.css`); copy one, change its colors, and name it in `theme`. The seed tasks and the board's title live in the inputs file, which `run.py` writes to `config.js`.

Needs Node: a component, a page, or a dependency. Edit `src/`, then in this folder run:

```
npm ci
npm run build
rm -rf node_modules
```
