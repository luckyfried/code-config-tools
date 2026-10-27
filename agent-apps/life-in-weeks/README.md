# Life in Weeks

## What this makes

A life calendar page, `out/life-in-weeks/`, that opens in any browser and prints as a poster. Ninety rows of fifty-two squares, one square per week of a life: the weeks already lived are filled, sweeping in from the top-left corner when the page opens; the eras (school, a city, a job) are tinted bands with their names in the left margin; single dates are marked squares with a hairline to a word in the right margin; and this week pulses once a second. Hovering a square shows its dates and the age then. On a phone the grid fills the screen and the era names move into the key and the tooltips. The Print button makes an A2, A3, A4, or Letter poster: the name and birthdate above, the grid centered, the chosen line below, and the eras as a key.

It needs one file in your project, `life-in-weeks.inputs.json`. `inputs.example.json` in this folder shows every key with a note on each:

- `name`: the name at the top of the poster.
- `birthdate`: the day the grid starts, `YYYY-MM-DD`.
- `years`: the rows, one per year of age; 90 by default.
- `eras`: three to eight stretches of life, each with `from`, `to` (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, or `"now"`), a `label`, and a `color` such as `"#5E8C6A"`.
- `events`: single dates to flag, each with a `date` and a `label`. A date still to come is marked too.
- `quote`: the line under the grid. Put a name after ` — ` to credit it.
- `paper`: `A2`, `A3`, `A4`, or `Letter`.
- `theme`: `paper` (bone white, lived weeks in ink), `ink` (black, lived weeks in bone), or `auto` (paper by day, ink when the device is set to dark).

Ask the person, in one message: "What's your birthdate? What three to six eras would you mark, with their years (school, a city, a job)? Any single dates to flag? A line for the bottom of the poster?" Then pick a color for each era that sits well beside the others, and ask which paper size they print on if they mention printing.

## Run

Run it once from the project folder before asking for anything, so the person sees the sample life first. With no `life-in-weeks.inputs.json` in the project yet, copy `inputs.example.json` there under that name; when the person's file is there, use it as it is:

```sh
cd <project> && cp -n <agent-apps root>/life-in-weeks/inputs.example.json life-in-weeks.inputs.json
cd <project> && python3 <agent-apps root>/life-in-weeks/scripts/run.py
```

`scripts/run.py` reads `life-in-weeks.inputs.json`, checks every key, and writes `out/life-in-weeks/`: the page, `config.js` with the inputs, `data.js` with the life worked out into weeks (the birthdate, the weeks lived on the day of the run, and the squares of each era and event), and `theme.css` with the chosen theme. A missing or wrong key is named in one line and nothing is written. Running it again on the same inputs on the same day writes the same files.

## Check

1. `out/life-in-weeks/data.js` holds the person's birthdate, and its `lived` is the number of whole weeks since then.
2. Serve the page (see Host) and open it. The lived weeks fill in from the top-left corner within a second and a half, and this week's square pulses.
3. The grid's `data-lived` attribute equals the number of filled squares: in the browser console, `document.querySelector(".weeks").dataset.lived` and `document.querySelectorAll(".weeks rect.lived").length` give the same number.
4. Every era is a tinted band with its name in the left margin on a desktop, and in the key under the grid.
5. Hover a square: the tooltip shows its dates and the age then.
6. Press Print, or print the page: the preview shows one poster page with the name and birthdate above the grid and the line below it.
7. The browser console shows no errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/life-in-weeks
```

Then open http://localhost:8000/. The page is served, never opened as a file, because browsers refuse its modules from a file address. The folder is plain files, so any static host serves it as it is, and it keeps working after the session ends.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com. It sends no data anywhere. To remove it, delete the `<script src="./badge.js" defer></script>` line from `index.html` in this folder's `site/` and run `run.py` again.

## Make it yours

Nothing here needs a build; change a file and run `run.py` again.

- Every key in `life-in-weeks.inputs.json`: the name, birthdate, rows, eras, events, the line, the paper size, and the theme.
- A theme: copy `site/themes/paper.css` to a new file in `site/themes/`, change its colors, and set `theme` to the file's name. Every color on the page, the lived weeks, the bands' tint, and the accent included, comes from those variables; `site/styles/` names none.
- The poster's composition: `site/styles/print.css`. Every length there is a multiple of `--pitch`, one week's square, worked out from the paper size, so one change holds for every size.
- The sweep's length: `--motion-sweep` in the theme file.
- The type: Fraunces and Inter ship in `site/vendor/fonts/` with their licenses; swap the files and the names in `site/styles/fonts.css`.
