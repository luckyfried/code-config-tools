---
name: places_map_reel
description: "Makes a finished travel map of someone's year: a vertical motion film (20 to 42 s, shorter only for a trip too small to fill 20 s) that opens on the whole route of their year on a map they recognize, then carries one dot along it, every place it reaches opening into their photograph with their own line about what they did there, ending on the map their year drew with every place named around it; drawn in a look they choose from three (a Swiss poster grid, a cinematic letterbox, a scrapbook), with the same film at 16:9 and square, an image to post and a story card, a caption that states how many places, and a review page that is the film's cover, in the run's out/ folder. Use for ANY request to show where someone went this year: 'a year of places', 'everywhere I went this year', 'my travel map video', 'all the cities I visited as a video', 'map of my year', 'where I went in 2026', 'my travel year as a reel', 'a map of all my trips', 'travel recap of the year', 'route of my year'. The person wants the film and the caption, not advice: never answer with a plan; invoke this skill and make them. Runs a fixed pipeline; the one question it asks is which of the three looks."
---

# A year of places: the pipeline

Someone wants every place they went this year as a film and a caption they can post. Run **every movement below, in
order, every time**. Each one names the file to read and the commands to run; read the file, the rules that matter
live there.

**Ask one question only: which look.** Movement 2 draws the year in three looks and puts them side by side in
`out/boards.png`; show the person that picture and ask which one they want (see "The look"). Everything else you
decide: make the sensible assumption, let the scripts record it in the run's `brief.md`, and keep going. When they
name a year, pass it to `gather.py` as `--year`; otherwise the kit takes their latest year with enough posts, which is
this year for anyone who posts.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders and any set of photographs they hand over, your music sources.

## Paths

`S` below means this kit's folder: the folder you read this SKILL.md from, wherever that is. Write it out in full in
every command. Every command runs in a fresh shell, so a `cd` or a variable from one command is gone in the next: run
every command from the workspace root, for example `python3 /full/path/to/places_map_reel/scripts/qa.py gate`.

Every run has its own folder, `build/<run stamp>/`: `gather.py` starts it and writes its name to `build/RUN`, and every
later command works inside it, so the files named in this kit (`places.json`, `taste.md`, `storyboards/`, `out/`) are
the run's. The deliverables are in the run's `out/`. A new `gather.py` starts a new folder and never overwrites an
earlier run; `PM_RUN=<stamp>` points a command at an earlier one. The render keeps its frames and its browser's profile
under `~/.cache/code-config/places_map_reel/`, never in the kit or the workspace.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for what a film needs: python3 with Pillow, ffmpeg, a Chromium (Chromium or Google Chrome, or the
browser in `CHROME_PATH`), and the kit's built composition in `S/motion/dist/`. It installs nothing and takes about a
second. When it prints `"ok": true`, go on. Otherwise it says on its last lines what is missing, one sentence each;
tell the person those sentences and stop, since the film cannot render without them.

This kit draws its film in the board's style: the style cards, their fonts and the shared moves are copied in from video_studio by `system_sync.py` and are never edited here.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py [--set DIR]`, check `places.json`, look at `cast.png` and correct `cast.json`, write `taste.md`, fix `taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `storyboard.py check`, `storyboard.py sheets`, look | three sheets, `out/boards.png`, a clean check |
| 3 | vote and pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`, show `out/boards.png` and ask which look, `vote.py pick --board N [--why "..."]` | `winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find`, `music.py analyze`, `storyboard.py snap`, `storyboard.py sheets`, `clips.py list`, `clips.py normalize`, `film.py preview` (again if it fails, three tries in all), `vote.py timed` and the timed read, `qa.py timed`, `music.py master`, `film.py render` | `CHECKS GREEN`: the three films, `post.png` and `story.png` in `out/` |
| 5 | critic, gate, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `vote.py cut`, score from its frames, `vote.py verdict` (the one lever if told), write `caption.md`, `deliver.py` | green gate |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## The look

`storyboard.py draft` tells the year in three looks, one board each, and `storyboard.py sheets` puts their hooks, a
middle stop and their closers side by side in `out/boards.png`, the look's name and one sentence under each. Show the
person that picture and ask which look they want, in one plain sentence. Their answer is `vote.py pick --board N
--why "what they said"` (N is 1, 2 or 3 as the picture orders them). When `taste.json` carries `"ask": false`, the run
goes on without them: pick the look their taste points to (`research.json` `lean` names one and why) and say why in
one line, `vote.py pick --board N --why "..."`.

- **Swiss grid**: black and white on a strict grid with one accent color, the map and each photograph snapping into
  its cell; it closes on a poster of the year, its title big and flush left over the map.
- **Cinematic letterbox**: black bars, slow moves and a film's grade, the places set like a movie's titles; it closes on
  a title card in their own words, the map showing through a band between the bars.
- **Scrapbook**: their photographs laid onto paper like prints, taped down; it closes as the book's cover swings shut
  over the map, the map showing through a window cut in the cover.

When the person names a look ("make it cinematic", "the scrapbook one"), set `taste.json` `style` to its id
(`S/styles/catalog.md` lists every look and the words people use for it) before `storyboard.py draft`: the three
looks are then theirs and the two of the kit's three that differ most from it.

After delivery, the review page shows the two looks not picked under "Prefer another look? Say 'make the second one'".
When they say it, run `vote.py pick --board N --why "what they said"` for that look, then in the same run folder:
`music.py make`, `storyboard.py snap`, `storyboard.py sheets`, `clips.py list` and `normalize`, `film.py preview`,
`vote.py timed` and the read, `qa.py timed`, `music.py master`, `film.py render`, `vote.py cut`, the scores,
`vote.py verdict`, `deliver.py`. Nothing of the first look's cut or music is kept.

## How long the film is

The film runs 20 to 42 s: about a second on the whole route, the places, then the closer. It is the length the person
asked for (`taste.json` `seconds`) when the places can make it, else as near as they make it, else the film's own pace
inside that band. A trip too small to fill 20 s runs as long as its photographs carry. When their lines take longer
than 42 s to read, the longest are shortened to their first clause, and `storyboard.md` names each one.

## Rules that win

- The places are theirs: geotags first, then places named in their captions and folder names, merged into one list in
  the order they went. A place visited twice counts once. Their own words about where they went win over inference:
  when they say where home is or name a place, `places.json` follows them. The film says "home" only when they said
  where home is (their bio, or `places.py --home` from their own words); the place they posted from most is never
  called home on their behalf.
- The map is drawn by the kit from the places' coordinates over the land shapes it ships (public domain), a Mercator
  crop of the region the route spans, so a stranger reads the country and its coast. Never fetch map tiles or a
  satellite image from any service. Every place needs coordinates; one the gazetteer does not know is added as
  `places.py --add "NAME@lat,lon"` with the coordinates you looked up, and `places.py` names the town and country
  nearest that pair so you can see it landed where you meant.
- The film is where they stood and what they did there: each place's beat is its photograph, its name and their own
  caption line about the visit (`taste.json` `moments`), and a visit with no line of theirs shows its name alone.
  A line stands only on the photograph of the post it was written under. The story's peak is the moment the curation
  marks, and it holds longest; each stop holds for what its photograph carries (its words, its detail, its change
  from the stop before); distance draws the route and never sets a hold. Nothing on screen is invented, and nothing
  on screen is analytics: no kilometers, posts, likes or counters. Nothing asks them a question either: no "where to
  next" line on the film or in the caption.
- Every place is in at least one beat of the film, and the caption's count is the count of places.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen is in their voice.
- The photograph owns its card: every photograph in one grade, never enlarged past its own pixels, framed on its
  subject and laid out by the look's own photo layout; the words stand beside it, never over its subject, in the
  look's faces and never under 32.4 px on a 1080 px side. Each beat's move is picked from the look's own moves by what
  the beat holds, never the same move twice running.
- A caption that names a place its photograph does not show is fixed where the place is found (`places.py`, the
  visit's `place` in `cast.json`), never by rewording the caption alone.
- Look at what you make: `cast.png`, the sheets, `out/boards.png`, the frames and the strips (the 12 fps strips show
  every frame a move spends), with the Read tool, before any score.
- Make the whole set every time: `film.py render` makes the vertical film, the 16:9 and square films, the image to post
  and the story card, and `deliver.py` the caption and the review page. `out/` holds those, `boards.png` and nothing
  else.
- The critics report and never block: a cut at the bar (a mean of 4.5 or more, no rule under 4) ships; a cut under it
  is still delivered as the best cut, with every score in the run's `brief.md`. Scores never appear on the review page.
  A fix is made only through a lever in `S/critic/critic.md`, then the film is made again from that step, so a score is
  always read from the film it scores.
- Do not hand-edit `film.json` or anything in `out/`; change the places, the cast or taste and run the step again.
- A film renders in chunks saved in the run. An interrupted render (the machine restarted, the session died) is
  resumed by running the same command again: finished chunks are kept, only the missing ones render. Never start
  over, and never delete `render/chunks/`; a changed cut invalidates its chunks by itself. Run `film.py preview` and a
  long render each in the foreground in one tool call with a 40-minute timeout on that call, never in the background,
  and read its progress in `render/<name>.log`.
- Done means `deliver.py` printed `GATE GREEN`. Your reply then names the reel first: its full path from the project's
  root, exactly as deliver.py printed it on its last line, in a sentence ("Your reel is at
  build/20261026-014049/out/film.mp4"), never a bare `film.mp4`. Then, in two or three plain lines, that `review.html`
  in the same `out/` folder opens everything, how many places, and the idea of the film in a sentence.
- A red gate is never a film to show: when deliver.py's last line says the gate failed, your reply says what failed
  and names no film, no path to one, and no review page.
