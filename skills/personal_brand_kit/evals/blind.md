# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- what's my style? make me a brand kit from my feed
- define my aesthetic
- make me a content style guide from my instagram
- what should my feed look like?
- turn my feed into a brand guide

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with one planted system (the docstring of
`make_person.py` lists it): a feed led by four named colors (terracotta 40%, cream 27%, olive 20%, chocolate 13%),
four pillars (table 45%, market 25%, streets 18%, coffee 12%), a lowercase voice with three recurring devices, posts
on Tuesday 08:00, Thursday 12:30 and Sunday 18:30, a `liked-posts/` folder in an aspirational coastal palette
(sea blue, ice blue, snow white, deep navy), and five posts that break the system. It ships as an Instagram export
in the JSON layout plus a small Facebook export, and builds in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/personal_brand_kit"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "what's my style? make me a brand kit from my feed" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export and likes doors; `brief.md` lists all of them.
- **No music.** The export carries none, so `music.py find` makes a bed in the
  mood of the person's music brief; `brief.md` names the origin and why.

## Pass

The run ends in its own folder `build/<run stamp>/` (named in `build/run`) with `out/film.mp4`, `out/brand.json`,
`out/plan.md` (30 dated entries), `out/caption.md`, `out/review.html`, `out/film-square.mp4`, `out/film-wide.mp4`,
`out/story.png` and `out/post.png`, no stills (no phrasing asks for them), and `brief.md` beside `out/`;
`python3 S/scripts/qa.py gate` prints `GATE GREEN`; the agent's last reply names `build/<run stamp>/out/film.mp4`
first, as deliver.py printed it; the three looks' sheets `storyboards/{a,b,c}/sheet.png` with their `storyboard.md`,
the boards side by side in `out/boards.png`, `vote.md`, `winner.json`, and the cut's scores in `critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,profile,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 High at 1080x1920, 30/1, for the film's length, and an aac track. Then the cut's strip `cut-strip.png` for
the eye.

## Found against intended

`out/brand.json` is read against the planted system: the four palette names and shares (each within a few points
of the plan), the four pillars and their shares in the same order, the three cadence days, the coastal aspire
palette, and the five outliers on the stop list. The film shows their own photographs as the moments the story
names, each with its own caption line, and no share or count on screen.

## Judging

Every film, with and without the kit, is judged on the criteria in `S/critic/critic.md` by eye: the sheets, the
boards, the strips, the films.

## The kit's tests

From the kit's folder:

```
python3 -I -m unittest discover -s tests
```

`tests/fixture.py` writes one person's run as `storyboard.py draft` reads it, with small photographs drawn when Pillow
is there; the tests that need the photographs skip without it, and the rest need only the standard library.

- `test_boards.py`: the three looks drafted from that run, each board in every format inside the rules `storyboard.py
  check` holds it to, every word on screen one of theirs, each beat's move chosen from what it shows, the question
  held long enough to read, labels large enough to read, and the peak and the hook's rest named for the cover and the
  image to post.
- `test_palette.py`: every palette rule a card may name gives a board's six colors from the feed's own.
- `test_verdict.py`: the bar, the one fix of round 1, the spent budget of round 2, and the pick (the person's, or the
  agent's with its reason when `ask` is false).
- `test_snap.py`: only the picked look is cut, and a new draft clears the old pick and its scores.
- `test_music.py`: the music is the person's own track, or a bed composed from the picked look's recipe, laid under the
  board's cues.
- `test_material.py`: the story's moments, in their order, and the hook's photograph.
- `test_qa.py`: the placeholder scan, the closer's still, where the hook puts its photograph's subject, the render
  report, and the audio rows.
- `test_what_was_asked.py`: what every run delivers, the stills only when asked for, and the reel's path last.
- `test_deliver.py`: the caption, the review page with no score on it, and `brief.md` with the cut's scores.
- `test_kill_points.py`: a command stopped at any point leaves nothing the next command reads wrongly.
- `test_research.py`, `test_gather.py`, `test_still.py`, `test_chunks.py`: the posting days and an outlier's voice,
  the export's media lookup, the still-frame reading under grain, and the resumable render.
