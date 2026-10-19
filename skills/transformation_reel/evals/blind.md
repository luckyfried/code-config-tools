# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make a before and after of my pottery
- my pottery progress video
- turn fourteen months of my pottery into a reel
- make a progress video (names nothing: the kit finds the subject)
- glow-up reel of my ceramics

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), as an Instagram export in the JSON layout and a small
Facebook export, with one subject tracked over fourteen months: her pottery, 24 posts and 2 reels from 2025-08-09
(day one at the wheel) to 2026-10-14 ("fourteen months in"), interleaved with about 140 unrelated travel and food
posts. The pottery photos progress with the date (one lumpy raw-clay bowl becomes a shelf of tall glazed pieces);
four posts are milestones and say so in their captions (2025-10-18, 2026-01-24, 2026-05-16, 2026-09-12). A second,
shorter run, her balcony garden (9 posts, 2026-04-05 to 2026-09-20), makes subject detection a real choice.
`liked-progress/` holds 12 progress posts she liked (seven left and right, three top and bottom, one four-up, one
single). The intended timeline is printed in the summary. It runs in well under 90 s.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/transformation_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make a before and after of my pottery" \
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
  session"`: every clip of the winning board is substituted with an animated treatment of one of their photos,
  a clip of their own reels stays as it is, and `brief.md` says which clips were substituted and why. The
  generated-clip path is proven by hand instead: copy one of the fixture's reels (`instagram-*/media/reels/*.mp4`)
  to `build/clips/01.mp4` as a stand-in for the model's output and run `clips.py normalize`; it arrives as
  "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, `out/then-now.png` (1080×1350), `out/caption.md`, `out/review.html` and
`out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets
(`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 30–60 s and an aac track. `build/subject.json` names pottery, 2025-08-09 to
2026-10-14, "14 months", and the four milestones above; the film's first photo beat is p01 (2025-08-09) and its last
is the latest post (2026-10-14). Then one frame per beat for the eye: `python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
