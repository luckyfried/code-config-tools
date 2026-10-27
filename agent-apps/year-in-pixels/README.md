# Year in Pixels

## What this makes

One page: a year as twelve months of thirty-one squares, one square for every day. Tapping a day raises five
mood swatches around it; picking one colors the square. On opening, the colored days pop in down each month in
turn, the days still to come are faint dots, and today pulses. A ribbon under the grid shows each month as a
blend of its moods. Tapping the legend opens the Stats sheet (each mood's count and longest run, the best month,
and the week's shape). On a desktop, hovering a day shows its date, mood, and note. The Export, import, and print
sheet saves every colored day as a file, adds days back from such a file, and prints the year as an A3, A4, or
Letter poster with the name and the year in a large serif above the grid and the legend below it. The page works
on a phone and a desktop, in a light look and a dark one, and keeps what the person colors in their browser.

## Run

Put `year-in-pixels.inputs.json` in the project folder (copy `inputs.example.json` from this folder and change
it), then:

```
cd <project> && python3 <agent-apps root>/year-in-pixels/scripts/run.py
```

It writes `out/year-in-pixels/` in the project. Running it again rewrites the folder from the inputs file. A
missing or wrong key stops the run with one line naming the key. When two mood colors are too close to tell
apart, the run says which two and still writes the page.

## Check

- `out/year-in-pixels/config.js` carries the name, the year, and five moods.
- Open the page (Host, below). The grid has 365 squares (366 in a leap year), the legend shows the five moods,
  and today has a pulsing ring.
- Tap a day before today and pick a mood: the square takes its color. Reload the page and it is still colored.
- In Export, import, and print, press Print: the print dialog shows one page with the name and the year above the grid.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/year-in-pixels
```

Then open http://localhost:8000/. The folder is plain files, so any static host serves it as it is. The page
reads today's date when it opens, so a hosted copy moves forward a day at a time without a new run. Each browser
keeps its own colored days; Export and Import carry them from one browser to another.

## Make it yours

Ask the person, in one message: "What name goes on the poster, and which year should it start on? Do you want
your own five moods, from your roughest day to your best, each with a word and a color, or the ready ramp from
cool blue to warm red?" Then write their answers into `year-in-pixels.inputs.json` and run again. Every key is
described in `inputs.example.json` under `_notes`:

- `name` and `year` are required.
- `moods` is exactly five `{ "id", "label", "color" }` entries, roughest first. Without it the ramp in
  `inputs.example.json` is used.
- `weekStart` is `mon` or `sun`, for the week row in the Stats sheet.
- `paper` is `A3`, `A4`, or `Letter`.
- `theme` is `auto` (follows the device), `gallery` (white, soft tiles), or `night` (black, glowing tiles).
- `example` set to `true` opens a first visit on an example year up to yesterday, so the person sees a full grid;
  `false` opens it empty. A person keeping their own year wants `false`, or clears the year in Export, import,
  and print.

To change a look itself, edit the color values in `site/themes/gallery.css` or `site/themes/night.css`
(`auto.css` carries both). No build step is needed for any of these changes.
