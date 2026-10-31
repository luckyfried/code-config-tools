# Blind run

A fresh agent, one person's export, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make my instagram year in review
- recap my year on instagram
- make me an instagram wrapped for 2026
- can you make a 2026 recap reel from my posts
- what did I post this year? make it into something I can share

## The fixture

```
python3 S/evals/fixtures/make_export.py S/evals/fixtures/books/<book>.json SANDBOX
```

writes one person's year as the Instagram "Download your information" export (the JSON layout: posts with captions
and times, per-post likes and comments, the profile, the media), from a book and the real photographs in `S/evals/fixtures/photos/` (`SOURCES.md` there names where each
comes from), so the fixture needs nothing outside the kit:

- `tomas.json`: Tomás Reis (@tomas.travels), a year of travel with friends: Lisbon with Rui, Sintra, the
  Dolomites, Marrakech and Fes;
- `ines.json`: Inês Moreira (@ines.at.home), a year at home and in the garden with friends and family: the cabin with
  Rita, Marta's birthday walk in Porto, Provence with Inês's mum.

Each month's photograph is the month's own post, its caption what happened that month, in their voice, with the people
tagged and the place named; the month's other posts are details of it, captioned shorter. Every caption agrees with
its photograph, so a caption never contradicts the picture it is posted with; a book whose caption does is fixed
in the book. It runs in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills"
python3 S/evals/fixtures/make_export.py S/evals/fixtures/books/ines.json "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/ig_year_in_review"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make my instagram year in review" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no MCP
config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The without-kit
run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** `gather.py` records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every clip stands in as the film's own move on the still photograph, and `brief.md` says which and why.
- **No music.** The export carries none, so `music.py find` composes a bed from the picked look's own recipe and the
  person's music brief; `brief.md` names the origin.
- **No one to ask which look.** The run is headless, so the agent sets `taste.json` `ask` to false and picks the look
  by taste with a one-line reason (`vote.py pick N --why`).
- **Reading the photographs.** Movement 1 has the agent open `build/picks-sheet.jpg` and write each month's `line`
  and `scene` into `build/picks.json` from what the photograph shows; the storyboard refuses a month without a scene.

## Pass

The run ends with `out/film.mp4`, `out/carousel/` (10), `out/stories/` (3), `out/strip/`, `out/looks/`,
`out/boards.png`, `out/caption.md` and `out/review.html`, and nothing else, with `build/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three `build/storyboards/<style>/sheet.png`,
`build/vote.md`, `build/critic/timed.json` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080x1920 at 30/1 for 6 to 90 s (under a minute for these full years) and an aac track. Then the strip for the eye:
`ffmpeg -i out/film.mp4 -vf "fps=12,scale=-2:300,tile=12x3" s-%02d.png`.

## Judging

Every film, with and without the kit, is judged on the seven criteria and the four reads in `S/critic/critic.md`, by
eye: the strips, the sheet, the film, and the measured checks in `build/qa/check.json`.
