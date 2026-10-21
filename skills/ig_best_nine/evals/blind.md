# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make my best nine
- make my top nine for 2026
- turn my most liked posts this year into a video
- what were my top 9 posts this year? make the grid and a reel
- best nine please

## The fixtures

A set's captions are written from its photographs, never separately.

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (120 posts, 25 reels, 60 stories, 900 likes across 40
accounts, saves, 200 comments, followers and following, per-post insights, media), a small Facebook export (posts
and albums), photos in one palette (portrait and square, some named `.heic` that are JPEG inside), four short mp4
reels. July is clearly the busiest month. Her nine most-liked posts stand clear of the tenth (a gap of more than
a hundred likes), spread across the year, include two reels, and carry captions that say why they worked. It runs
in a few seconds.

```
python3 S/evals/fixtures/make_bakery.py SANDBOX PHOTOS
```

writes a bakery's Instagram export (@cornerloaf: posts, per-post likes and comments, the username) whose posts
name the photographs in the folder `PHOTOS` by file name and copies none of them. Run the pipeline with
`BEST_NINE_PHOTOS=PHOTOS` and the nine are read from that folder at full size: the run a person makes when their
photographs live beside the download.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/ig_best_nine"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make my best nine" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.
- **No graphics card.** The render runs on the processor; brief.md says which one made the film.

## Pass

The run ends with one run folder `build/<stamp>/` whose `out/` holds `film.mp4`, `film-square.mp4`, `film-wide.mp4`,
`best-nine.png` (1080x1080), `story.png` (1080x1920), `caption.md`, `review.html` and `brief.md`;
`python3 S/scripts/qa.py gate --run build/<stamp>` prints `GATE GREEN`; the three sheets
(`storyboards/<tone>/sheet.png`), `vote.md`, `critic/timed.json` and the cut scores in `critic/` exist in the run;
and

```
ffprobe -v error -show_entries stream=width,height,codec_name,profile,r_frame_rate,duration -of csv build/<stamp>/out/film.mp4
```

shows h264 High 1080x1920 at 30/1 for 15 to 30 s and an aac track. The run's `frames/` holds the hook, the densest
beat and the closer of every format for the eye.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
