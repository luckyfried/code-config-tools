# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- Recap my Amalfi coast trip
- make a travel reel from my amalfi posts
- our week on the amalfi coast as a video
- travel recap please
- vacation video from my posts

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), with a clear everyday taste (film-grain travel and food
in warm earth tones): an Instagram export in the JSON layout (about 120 posts, 27 reels, 60 stories, likes, saves,
comments, followers and following, per-post insights, media) and a small Facebook export (posts and albums). Two
trips stand apart and only they carry geotags: six days on the Amalfi coast (2026-10-03 to 2026-10-08; posts and
stories every day in napoli, capri, positano and amalfi; @dani.reyes and @theo.makes tagged throughout; four short
clips she shot there; captions that name the places; a Facebook album; a cool palette unlike her everyday one),
and three days in Copenhagen in March, so "the most recent trip" has to be chosen. It runs in a few seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/trip_recap_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "Recap my Amalfi coast trip" \
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
  session"`: every generated clip of the winning board is substituted with an animated treatment of one of her
  photos, her own trip clips are cut from her footage, and `brief.md` says which clips were substituted and why.
  The generated-clip path is proven by hand instead: copy two of the fixture's reels
  (`instagram-*/media/reels/*.mp4`) to `build/clips/01.mp4` and `02.mp4` as stand-ins for the model's output and
  run `clips.py normalize`; they arrive as "generated".
- **No music.** The export names none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, `out/film-16x9.mp4`, `out/story-1.png` .. `out/story-5.png`, `out/caption.md`,
`out/review.html` and `out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets
(`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film-16x9.mp4
```

show h264 1080×1920 and 1920×1080 at 30/1 for 30–60 s (the two within 1 s of each other) and an aac track. The
brief names all four places and every one of them appears in a beat. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the films.
