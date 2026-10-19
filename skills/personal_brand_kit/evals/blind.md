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
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every clip of the winning board is substituted with an animated treatment of one of their photos,
  and `brief.md` says which clips were substituted and why. The generated-clip path is proven by hand instead:
  copy two of the fixture's reels (`instagram-*/media/reels/*.mp4`) to `build/clips/01.mp4` and `02.mp4` as
  stand-ins for the model's output and run `clips.py normalize`; they arrive as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, the ten cards `out/cards/01-palette.png` .. `10-week.png` (1080×1350 each),
`out/brand.json`, `out/plan.md` (30 dated entries), `out/caption.md`, `out/review.html` and `out/brief.md`;
`python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets (`build/storyboards/N/sheet.png`),
`build/vote.md` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 20–30 s and an aac track. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Found against intended

`out/brand.json` is read against the planted system: the four palette names and shares (each within a few points
of the plan), the four pillars and their shares in the same order, the three cadence days, the coastal aspire
palette, and the five outliers on the stop card.

## Judging

Every film and guide, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye:
the frames, the cards, the sheets, the film.
