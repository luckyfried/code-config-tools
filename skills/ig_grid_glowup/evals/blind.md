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
and albums), and photos in one palette (some named `.heic` that are JPEG inside). The last 30 posts carry plain
problems: a run of five posts in a clashing palette, three tight crops among wide scenes, and two text screenshots.
The account's likes and saves, and its own numbers on the grid, point at a quiet tonal feed. Stories, carousel slides and the
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
- **No image or video model.** The posts are the person's own photos and the films are drawn by the kit's own
  film composition, so neither is needed.
- **No music.** The export carries none, so `music.py find` composes a bed from the picked look's own recipe, at the
  board's tempo, so the cuts land on its beat; `music.json`'s origin says so.

## Pass

The run's `out/` (`build/<run stamp>/out/`, the run named in `build/RUN`) holds the deliverables and nothing else:
`film.mp4`, `film-landscape.mp4`, `film-square.mp4`, `posts/NN.png` (1080×1350 each), `story.png` (1080×1920),
`caption.txt`, `grid-after.png`, `boards.png` (the three looks) and `review.html`, which opens on the reel. Beside `out/` are `audit.md` (at least
three findings), `grid-before.png`, `plan.md` (the captions in order) and `brief.md`. `python3 S/scripts/qa.py gate`
prints `GATE GREEN`; the agent's last reply names `build/<run stamp>/out/film.mp4` first, as deliver.py printed it;
`clips/requests.json` holds the hook's world, the stills brought to life and the textures, each a shot with its lens,
light and move; the three `storyboards/<L>/sheet.png`, `vote.md`, `winner.json` and the cut scores in `critic/` exist; and `qa/check.json` shows the reel
at its size, H.264 High at 30 fps, with an AAC track at −14 LUFS. The films' settled frames are in `frames/` for the
eye.

## Judging

Every run, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the posts
against the real grid, the three boards, the films' frames.
