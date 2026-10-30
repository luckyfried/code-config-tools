# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing,
finds the named one, and carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make a birthday video for @dani.reyes, she turns 30 on october 24
- birthday tribute reel for my friend dani
- make a video for dani's 30th
- anniversary video for us
- something for our five years

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones), as an Instagram export (posts, reels, stories, likes, saves, comments, followers, insights, media)
and a small Facebook export. Her friend Dani Reyes (@dani.reyes) has a clear shared history across the year:
tagged in twenty or more posts and stories, in most of the group photos, a first photo together in January and a
latest one in October, more than forty comments traded in two distinct voices (Maren lowercase and warm, Dani
loud with emoji), a caption where Maren names the birthday (October 24, Dani turns 30) and two short videos the two
shot together. Every caption on a photograph is written from that photograph, so a film that sets a caption over
its picture never contradicts it. A second friend, @theo.makes, is the account Maren writes to most but shares far fewer photos with,
so the kit has to pick the named one and not the most frequent one. `dani.reyes-feed/` stands in for Dani's own
reachable feed: a dozen posts in a cool, bright palette unlike Maren's, so the palette the two share is derived.
It runs in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/birthday_tribute_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make a birthday video for @dani.reyes, she turns 30 on october 24" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or music tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door, and reads `dani.reyes-feed/` as the named one's feed; `brief.md` lists every door.
- **No music.** The export carries none, so `music.py make` has the music engine play the chosen look's recipe,
  turned by the person's music brief; `brief.md` names the origin.

## Pass

The run ends with `out/film.mp4` and no square film, wide film or stills (the request asked for a video),
`out/caption.md` (naming @dani.reyes or Dani), `out/review.html` and `out/brief.md`; the agent's reply names the reel
first by the path deliver.py printed last (`build/<run>/out/film.mp4`); `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the storyboard's three
sheets (`build/<run>/storyboards/1/sheet*.png`), `build/<run>/vote.md` and the cut scores in `build/<run>/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,profile,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 High at 1080×1920, 30/1, 20–60 s (within 1 s of a length the ask named), with an aac track. Then the three settled frames for the eye (the hook, the peak card, the closer):
`python3 S/scripts/film.py frames --out frames`, and the whole reel at two frames a second in `B/qa/film-strip2.png`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets and the film.
