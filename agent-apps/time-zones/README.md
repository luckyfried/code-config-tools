# Time Zones

## What this makes

One page with a row for you and a row for each person you work with. Every row is a strip of that person's day,
colored like the sky where they are (night navy, dawn, daylight, dusk), laid on your own day so the hours line up,
with a bar under it for their working hours. A line marks a time: drag it on a desktop, or scroll the day under it
on a phone. Every row shows its local time at the line, and where everyone is inside their working hours the column
glows and the heading says "Good for everyone". The Copy times button copies a line like
`Thu 15:00 Lisbon / 10:00 New York / 19:30 Bengaluru`. Each name has a small ticking clock, and picking a date
across a clock change moves the strip that changed and flashes its new offset. Arrow keys move the line by an hour,
and with Shift by fifteen minutes. The page works on a phone and a desktop, in a day look and a night look.

## Run

Put `time-zones.inputs.json` in the project folder (copy `inputs.example.json` from this folder and change it),
then:

```
cd <project> && python3 <agent-apps root>/time-zones/scripts/run.py
```

It writes `out/time-zones/` in the project and prints how many files it wrote. Running it again rewrites the folder
from the inputs file. A missing or wrong key stops the run with one line per problem, naming the key.

## Check

- `out/time-zones/config.js` carries your city and every person from the inputs file.
- Open the page (Host, below). There is one strip per person plus yours, and on today the line sits at your current
  time.
- Drag the line (or scroll on a phone) to an hour inside everyone's working hours: the column glows and the heading
  reads "Good for everyone". Press Copy times and paste: the line names every city.
- Pick a date across a clock change (for New York, the first Sunday of November): only the strips whose offset
  changed move, and their offset flashes.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/time-zones
```

Then open http://localhost:8000/. The folder is plain files, so any static host serves it as it is. The clocks and
the line read the time from the device that opens the page, so a hosted copy is always current.

## Make it yours

Ask the person, in one message: "Which city are you in, and what hours do you usually work? Who do you meet with:
each person's name, the city they are in, and the hours they work there?" Then write the answers into
`time-zones.inputs.json` and run again. Every key is described in `inputs.example.json` under `_notes`:

- `home` takes `label` (the city name shown), `zone` (a time zone name such as `Europe/Lisbon`), and optional
  `workStart` and `workEnd` (hours from 0 to 24 in quarter steps; 9 and 17 when left out).
- `people` takes one to twelve `{ "name", "city", "zone", "workStart", "workEnd", "color" }` entries in the order
  the page shows them. Hours past midnight work too, like `"workStart": 22, "workEnd": 6`. `color` is optional, a
  hex color like `"#e0457b"` that tints their working hours and their clock's seconds hand.
- `hourFormat` is `24` (15:00) or `12` (3:00 pm).
- `theme` is `auto` (follows the device), `day` (white page, bright strips), or `night` (black page, softer strips,
  a brighter glow). The sun and moon button on the page switches between them and remembers the choice.

To change a look itself, edit the color values in `site/themes/day.css` or `site/themes/night.css` (`auto.css`
carries both); the sky colors are the `--sky-*` values. No build step is needed for any of these changes.
