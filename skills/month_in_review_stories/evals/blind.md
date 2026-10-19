# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make my september recap stories
- my month in review
- october recap stories
- monthly wrap-up please, as stories
- what I posted this month as stories
- month recap

The fixture's month is September 2026, which is also the last full month before the fixture's end date, so a
phrasing that names no month lands on it too.

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (about 120 posts, 27 reels, 60 stories, 900 likes across 40
accounts, saves, 200 comments, followers and following, per-post insights, media), a small Facebook export (posts
and albums), photos in one palette (portrait and square, some named `.heic` that are JPEG inside), short mp4 reels.
September, a month in Marrakech, plainly differs from the rest of the year: a new subject (zellige tiles, the
Majorelle garden, a pottery class), a shifted palette (cobalt, indigo and saffron on cream), about three times the
usual cadence, and three posts (561 to 642 likes) that beat everything else of the year. It runs in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/month_in_review_stories"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make my september recap stories" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every clip of the winning board is substituted with an animated treatment of one of their photos, a
  clip of their own reels stays as it is, and `brief.md` says which clips were substituted and why. The
  generated-clip path is proven by hand instead: copy one of the fixture's reels (`instagram-*/media/reels/*.mp4`)
  to `build/clips/01.mp4` as a stand-in for the model's output and run `clips.py normalize`; it arrives as
  "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, three to five cards in `out/cards/` (each `NN-<role>.mp4` and `NN-<role>.png`),
`out/caption.md`, `out/template.json`, `out/review.html` and `out/brief.md`; `python3 S/scripts/qa.py gate` prints
`GATE GREEN`; the three style sheets (`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in
`build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

(and the same for every `out/cards/*.mp4`) shows h264 1080×1920 at 30/1 for 15 ±0.5 s and an aac track. Then one
frame per card for the eye: `python3 S/scripts/film.py frames --out frames` writes `frames/NN-<role>.png` and
`frames/sheet.png`.

## Judging

Every result, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film and the cards.
