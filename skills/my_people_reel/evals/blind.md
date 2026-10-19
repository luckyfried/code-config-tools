# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make a video of who I spent the year with
- my people of 2026
- make a friendship recap of my year
- turn my top friends of the year into a reel
- who did I hang out with most this year? make it a video and tag them

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear taste (film-grain travel and food in warm
earth tones): an Instagram export in the JSON layout (about 140 posts, 29 reels, 60 stories, likes across 40
accounts, saves, the posts others tagged her in, the comments she wrote and the comments others wrote on hers,
followers and following, per-post insights, media), a small Facebook export (posts and albums), photos in one
palette, and short mp4 reels. Her people are six recurring accounts with clearly different volumes, each the one
she is with most in one stretch of the year; eleven group photos and two short group reels tag several of them at
once; their comments come in six distinct voices; one of them (liv.outside) is tagged most of all and never
comments, so tags alone give the wrong order. The intended order, every signal counted once, is dani.reyes,
theo.makes, ines.walks, liv.outside, kofi.cooks (then sam_and_june, far below). It runs in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/my_people_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make a video of who I spent the year with" \
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
  generated-clip path is proven by hand instead: copy two of the fixture's reels
  (`instagram-*/media/reels/*.mp4`) to `build/clips/01.mp4` and `02.mp4` as stand-ins for the model's output and
  run `clips.py normalize`; they arrive as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, one `out/people/NN-<handle>.png` (1080×1920) per person, `out/caption.md` tagging
every one of them, `out/review.html` and `out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the
three style sheets (`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/` exist;
`build/people.json` ranks the five in the intended order; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 30–60 s and an aac track. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
