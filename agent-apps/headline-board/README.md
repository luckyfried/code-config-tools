# headline-board

## What this makes

A split-flap news board in one web page: your feeds' headlines roll across rows of flaps that spin through the
alphabet and land with a clack, with the time, the weather, and each story's source and age. Tap a row to open the
story. It fits a phone, a kitchen tablet, a desktop, and a big screen.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 <agent-apps root>/headline-board/scripts/run.py
```

`run.py` reads `headline-board.inputs.json` from the project folder. When the person has none yet, copy this app's
`inputs.example.json` there as `headline-board.inputs.json` first; it runs as it is. The run fetches the feeds and
the weather (ten seconds at most each), names any source that did not answer, and writes the board to
`out/headline-board/`. A missing or wrong input is named in one line and the run stops with exit code 2.

Run it again whenever the news should be fresh; on a schedule, once an hour keeps the feeds current. Wikipedia,
Hacker News, and the weather also refresh on their own while the page is open.

## Check

`out/headline-board/index.html` and `out/headline-board/feed.json` exist. `feed.json` holds the time of the run
(`updated`) and at least one headline for each source that answered. Served (see Host), the page opens on the board
spinning its letters into place, and the footer reads "Updated" with the time and the sources. If no source
answered, the board shows its sample headlines and the footer reads "Sample headlines". Adding `?demo=1` to the
address shows the sample board at any time.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/headline-board
```

then open `http://localhost:8000/`. Any static host can serve the `out/headline-board/` folder as it is, at any
path. Sound starts after the first tap or key press, which is when a browser lets a page make sound.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds.
A tap on it opens this app's page on code-config.com. It sends no data anywhere. To remove it, delete the
`<script src="./badge.js" defer></script>` line from `index.html` (in this app's `site/` folder, so every run leaves
it out).

## Make it yours

Every key in `headline-board.inputs.json` changes the board with no tools beyond Python; run `run.py` again after a
change.

- `title`: the name on the top plate.
- `sources`: RSS or Atom feed links, `"wikipedia"`, `"hackernews"`, and `"guardian"` or `"guardian:<section>"`
  (`"guardian:world"`, `"guardian:technology"`). A feed can be `{"url": "…", "tag": "LOCAL"}` to set the up-to-five
  letters on its colored flaps. Sources take turns down the board.
- `rows`: about how many headlines show at once, 2 to 12; it sets the size of the flaps. Each row takes exactly the
  lines its headline needs, and every page is as many whole headlines as fill the board, so a phone shows fewer,
  larger ones and a big screen more.
- `secondsPerFlip`: how long each page stays up before the board turns to the next, 3 to 120. The settings sheet on
  the board changes it for that screen too.
- `location`: `{"lat": …, "lon": …, "name": "…"}` for the weather line, or `null` to leave it off. Temperatures show
  in Fahrenheit for US English browsers and Celsius elsewhere.
- `theme`: `amber`, `white`, or `departures`. Each follows the screen's light or dark setting, and the settings sheet
  can pin one.

The Guardian needs a free Open Platform developer key. Ask for it through `csc key set GUARDIAN_API_KEY`, never in
chat; `run.py` reads it from the environment at run time and writes only the headlines, never the key.

Changing the look goes deeper without Node: the colors live in `site/themes/<name>.css` (a new file there is a new
theme name), the layout in `site/styles/`, and the board's behavior in `site/js/`; on a touch screen
`site/js/canvas.js` draws the flaps from the same theme colors. The flap timing is `--spin-ms` and `--land-ms` in
`site/styles/base.css`; the clack is rendered in `site/js/sound.js`.
