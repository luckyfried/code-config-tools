# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request (each names the product, the date and the asset folder):

- announce my launch: Tide Table, my ceramic tableware, drops November 14. product photos and a clip are in tide-table-launch/
- make a hype video for my drop: Tide Table on November 14, assets in tide-table-launch/
- countdown stories and a teaser for Tide Table, launching 2026-11-14, the photos are in tide-table-launch/
- promo for my new thing, Tide Table (plates and bowls), out November 14; everything's in tide-table-launch/

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX > fixture.log
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (about 129 posts, 27 reels, 60 stories, 900 likes across 40
accounts, saves, 200 comments, followers and following, per-post likes, comments and saves, media), a small
Facebook export, and `tide-table-launch/`, the product's own assets: six studio stills and one 5 s turntable clip in
a cool palette (cobalt, sea glass, lemon, porcelain, navy) distinct from hers. Her nine most-responded posts
(comments plus saves: 306, 278, 253, 215, 182, 159, 146, 129, 106) stand clear of every other post (none passes 45),
their likes run in a different order on purpose, and their openers come in three styles (question, confession,
list), three each. Four posts about Tide Table are already in her feed. It runs in a few seconds and prints the
intended values (the hook order, the date, the asset counts): keep that printout **outside** the sandbox, where
neither run can read it.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX" > /path/outside/fixture.log
cp -r S "$SANDBOX/.claude/skills/launch_hype_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "announce my launch: Tide Table, my ceramic tableware, drops November 14. product photos and a clip are in tide-table-launch/" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **The product's folder.** gather.py links its stills and its clip as the product's assets, never as her photos;
  every product beat and card shows one of them, and the turntable clip plays as "their footage".
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every generated clip of the winning board is substituted with an animated treatment of a product
  still, and `brief.md` says which clips were substituted and why. The generated-clip path is proven by hand
  instead: save any short mp4 as `build/clips/NN.mp4` for a clip that asks for generation and run
  `clips.py normalize`; it arrives as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, `out/story-1.png`, `out/story-2.png`, `out/story-3.png`, `out/countdown.png`
(each 1080×1920), `out/feed.png` (1080×1350), `out/captions.md`, `out/review.html` and `out/brief.md`;
`python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets (`build/storyboards/N/sheet.png`),
`build/vote.md` and the cut scores in `build/critic/` exist; `out/brief.md` ranks her hooks in the fixture's
intended order; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 15–30 s and an aac track. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the stills, the sheets, the film.
