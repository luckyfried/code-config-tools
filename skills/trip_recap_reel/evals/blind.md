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
clips they shot there; captions that name the places; a Facebook album; a cool palette unlike their everyday one),
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
- **No video model.** The film lists a clip per photograph; with no model none arrives, so `clips.py normalize --why
  "no video model in this session"` records each as a stand-in (the camera walks the still photograph) and cuts their
  own clips from the export into the stops they show.
- **No music.** The export names none, so `music.py find` makes the bed from their brief, its mood at its tempo;
  `brief.md` and the storyboard's `Music:` line name the origin.

## Pass

The run's folder (`build/<run>/`, named in `build/RUN`) ends with `out/film.mp4`, `out/caption.md`,
`out/review.html`, `out/cover.png` and `brief.md` beside `out/`, and no 16:9 or square film and no story card (no phrasing asks for one);
`python3 S/scripts/qa.py gate` prints `GATE GREEN`; the agent's last reply names `build/<run>/out/film.mp4` first,
as deliver.py printed it; the storyboard's sheet
(`storyboards/1/sheet.png`), `vote.md` and the cut scores in `critic/` exist; and, from the run's folder,

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 and an aac track. The
brief names all four places and the film names every one of them. Then the strips for the eye:
`python3 S/scripts/film.py frames` (`frames/film-strip.png` and one strip per span).

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheet, the films.
