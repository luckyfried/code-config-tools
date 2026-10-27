# Morning Paper

## What this makes

A newspaper front page with the person's own masthead, set fresh from the news sources they choose and sorted into
the sections they name, with a weather ear for where they live, On this day, the most-read article, and the picture
of the day. It opens by printing itself, reads as a six-column broadsheet on a desktop and a two-column tabloid on a
phone, and prints on A4 or Letter. Each story opens to its summary and a link to the full piece.

## Run

From the person's project folder, before asking for any personal details:

```sh
cd <project> && python3 .claude/agent-apps/morning-paper/scripts/run.py
```

`<project>` is the person's project folder and `.claude/agent-apps` is where this app sits inside it; use the real
path to `scripts/run.py` when the app lives elsewhere. The script reads `morning-paper.inputs.json` from the current
folder. When the person has none yet, copy this app's `inputs.example.json` there as `morning-paper.inputs.json`
first: it prints the sample edition with no network at all. The run writes the page to `out/morning-paper/`.

A wrong or missing key stops the run with one plain line naming it, and exit code 2. With `"live": true` the run
reads every source named in `sections` (each RSS or Atom feed, Hacker News, and the Guardian when its key is set),
and Wikipedia's featured feed and the weather for the day, into `out/morning-paper/feed.json` with the time it ran.
A source that does not answer is named and left out; the rest of the paper is still set.

## Check

- The run prints `Wrote out/morning-paper/ (… files).` and exits 0.
- `out/morning-paper/index.html` has the masthead inside `<h1>` and the edition's date in the dateline.
- `out/morning-paper/feed.json` exists and its `setAt` is the time of the run (the sample edition carries its own
  date, Monday, October 26, 2026).
- `out/morning-paper/paper.css` sets `@page` to the paper size in the inputs (`A4` or `letter`).
- Served (see Host), the page sets the masthead, wipes each column in, and shows the sections in the inputs' order.
  The sample edition says "Sample edition" in the right-hand ear. Adding `?demo=1` to the address shows the sample
  edition whatever the inputs say.
- The browser's print dialog shows the paper on the chosen size, with no buttons and no motion.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/morning-paper
```

then open `http://localhost:8000/`. Any static host serves `out/morning-paper/` as it is, under any path. A live
edition is a snapshot of the morning it was set; run the script again each morning (or on a schedule) for a fresh
paper. When the page opens it asks Wikipedia (On this day, Most read, the picture of the day) and Open-Meteo (the
weather) for the day's boxes, and keeps the copies baked in at run time if either does not answer.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds on
every visit. A tap opens this app's page on code-config.com. It sends no data anywhere. To remove it, remove its
script line, `<script src="./badge.js" defer></script>`, from `out/morning-paper/index.html` (or from
`site/index.html` in this app so every run leaves it out).

## Make it yours

Ask the person, in one message:

1. What the paper is called, and a motto for under the masthead (or none).
2. Which news sources they read, and which section each one goes in. Any site with an RSS or Atom feed works; Hacker
   News and the Guardian work too.
3. Where they are, for the weather ear (a town is enough; look up its latitude and longitude), and Fahrenheit or
   Celsius.
4. Broadsheet, tabloid, or evening; and A4 or Letter paper.

Then write `morning-paper.inputs.json` in the project folder (every key and its meaning is in `inputs.example.json`
under `_notes`), set `"live": true`, and run the Run line again.

| Key | What it does |
| --- | --- |
| `masthead`, `motto` | The paper's name across the top, and the line under it. |
| `sources` | Each source has an `id`, a `name` printed in bylines, and a feed address in `url`; or `"kind": "hackernews"`; or `"kind": "guardian"` with a Guardian `section` such as `"world"`. |
| `sections` | `{ "name", "sources": [ids] }` in print order. The first section's top story leads the front page; the next two sections' top stories sit beside the picture of the day. |
| `location` | `{ "name", "lat", "lon" }` for the weather ear. |
| `paper` | `"A4"` or `"Letter"` for the print view. |
| `theme` | `"broadsheet"` (cream newsprint, and the evening edition in dark mode), `"tabloid"` (white stock, red-top masthead, heavy headlines), or `"evening"` (cream on ink at any hour). |
| `units` | `"fahrenheit"` or `"celsius"`. |
| `live` | `true` sets today's paper from the sources; `false` prints the sample edition. |

The Guardian's own API needs a developer key: ask for it through `csc key set` as `GUARDIAN_API_KEY`, never in chat.
The run reads it from the environment and uses it to fetch the stories; the key is never written into the page or
anywhere under `out/`. The Guardian's public RSS feeds (for example `https://www.theguardian.com/culture/rss`) need
no key at all.

Nothing here needs Node or a build. Every input key, the theme, and the paper size change with a new run. The look
lives in files: `site/themes/<name>.css` holds a theme's colors and type as tokens only (copy one to make a new
theme, then name it in `theme`), `site/styles/` holds the layout and the press, and `site/app.js` sets the page. A
new theme file is picked up by name on the next run.
