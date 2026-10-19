# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- fix my grid
- make my feed look better
- plan my next nine posts
- my feed looks messy, can you do a grid glow-up
- grid makeover please

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (about 120 posts with carousels, 27 reels, 60 stories, likes,
saves, comments, followers and following, per-post insights with saves, media), a small Facebook export (posts
and albums), and photos in one palette (some named `.heic` that are JPEG inside). Her last 30 posts carry plain
problems: a run of five posts in a clashing palette, three tight crops among wide scenes, and two text screenshots.
Her likes and saves, and her own numbers on the grid, point at a quiet tonal feed. Stories, carousel slides and the
Facebook albums are the library the next nine come from. It runs in well under a minute.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/ig_grid_glowup"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "fix my grid" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser, image or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No image model.** A post that no photo of hers fits gets a painted still in its color; `build/stills.json`,
  the plan and `brief.md` say which.
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: both clips are substituted with an animated treatment of one of her photos, and `brief.md` says so.
  The generated-clip path is proven by hand instead: copy two of the fixture's reels
  (`instagram-*/media/reels/*.mp4`) to `build/clips/01.mp4` and `02.mp4` as stand-ins for the model's output and
  run `clips.py normalize`; they arrive as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/audit.md` (at least three findings), `out/grid-before.png`, `out/posts/01..09.png`
(1080×1350 each), `out/grid-after.png`, `out/plan.md` (nine captions in order), `out/film.mp4`, `out/review.html`
and `out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets
(`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 15 s ±0.5 s and an aac track. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Judging

Every run, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the nine
against the real grid, the sheets, the film's frames.
