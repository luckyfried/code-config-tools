# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request. The launch ones name the subject, the date and the asset folder, and
run on the fixture below:

- announce my launch: Tide Table, my ceramic tableware, drops November 14. subject photos and a clip are in tide-table-launch/
- make a hype video for my drop: Tide Table on November 14, assets in tide-table-launch/
- countdown stories and a teaser for Tide Table, launching 2026-11-14, the photos are in tide-table-launch/
- promo for my new thing, Tide Table (plates and bowls), out November 14; everything's in tide-table-launch/

The others run on a sandbox holding one folder of `evals/fixtures` (copied in as it is):

- make a hype reel for my friend Ines, everything about Ines is in friend/   (the friend fixture)
- hype up this idea of mine, the Sunday Soup Swap, it's in idea/   (the idea fixture)
- a reel about Harbourlight, an account I love, I saved their page in account/   (the followed account fixture)
- what could you make for me?   (the ideas fixture: `pulled/` is what a connected account gives, `project/` a project
  of theirs; the run offers three to five ideas first)

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX > fixture.log
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (about 129 posts, 27 reels, 60 stories, 900 likes across 40
accounts, saves, 200 comments, followers and following, per-post likes, comments and saves, media), a small
Facebook export, and `tide-table-launch/`, the subject's own assets: six studio stills and one 5 s turntable clip in
a cool palette (cobalt, sea glass, lemon, porcelain, navy) distinct from theirs. Their nine most-responded posts
(comments plus saves: 306, 278, 253, 215, 182, 159, 146, 129, 106) stand clear of every other post (none passes 45),
their likes run in a different order on purpose, and their openers come in three styles (question, confession,
list), three each. Four posts about Tide Table are already in their feed. It runs in a few seconds and prints the
intended values (the hook order, the date, the asset counts): keep that printout **outside** the sandbox, where
neither run can read it.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX" > /path/outside/fixture.log
cp -r S "$SANDBOX/.claude/skills/hype_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "announce my launch: Tide Table, my ceramic tableware, drops November 14. subject photos and a clip are in tide-table-launch/" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram or browser tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **The subject's folder.** gather.py links its stills and its clip as the subject's assets, never as their photos;
  every subject beat and card shows one of them, and the turntable clip plays as "their footage".
- **Their photographs.** With no `--feed`, the feed is the photographs of their posts with their captions and days; the
  cast reads what each shows from its caption, and a film plays as many of theirs as fit its parts (none makes it from
  the subject alone).
- **No music.** The export carries none, so `music.py find` makes the bed from their music brief; `brief.md` names the
  origin.

## Pass

The run's folder is `build/current/`. It ends with `out/film.mp4`, `out/story-1.png`, `out/story-2.png`, `out/story-3.png`, `out/countdown.png`
(each 1080×1920), `out/feed.png` (1080×1350), `out/captions.md`, `out/review.html` and `out/brief.md`;
`python3 S/scripts/qa.py gate` prints `GATE GREEN`; the style sheet (`storyboards/1/sheet.png`),
`vote.md` and the cut scores in `critic/` exist; `out/brief.md` ranks their hooks in the fixture's
intended order; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv build/current/out/film.mp4
```

shows h264 1080×1920 at 30/1 for 12–30 s (the length they asked for, held inside that) and an aac track. Then the strips for the eye:
`python3 S/scripts/film.py frames` (`build/current/frames/`).

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the stills, the sheets, the film.
