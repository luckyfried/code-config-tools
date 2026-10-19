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
loud with emoji), a caption where Maren names the birthday (October 24, Dani turns 30) and two short clips the two
shot together. A second friend, @theo.makes, is the account she writes to most but shares far fewer photos with,
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
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door, and reads `dani.reyes-feed/` as the named one's feed; `brief.md` lists every door.
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every generated clip of the winning board is substituted with an animated treatment of one of their
  photos, a clip of their own video stays as it is, and `brief.md` says which clips were substituted and why. The
  generated-clip path is proven by hand instead: copy one of the fixture's reels to `build/clips/01.mp4` as a
  stand-in for the model's output and run `clips.py normalize`; it arrives as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, `out/film-square.mp4`, `out/card.png` (1080×1350), `out/caption.md` (naming
@dani.reyes or Dani), `out/review.html` and `out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`;
the three style sheets (`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/`
exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film-square.mp4
```

show h264 1080×1920 and 1080×1080 at 30/1 for 30–60 s, within a second of each other, each with an aac track.
Then one frame per beat for the eye: `python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the films and the card.
