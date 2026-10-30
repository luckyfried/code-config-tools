# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make a before and after of my pottery
- my pottery progress video
- turn fourteen months of my pottery into a reel
- make a progress video (names nothing: the kit finds the subject)
- glow-up reel of my ceramics

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), as an Instagram export in the JSON layout and a small
Facebook export, with one subject tracked over fourteen months: their pottery, 24 posts and 2 reels from 2025-08-09
(day one at the wheel) to 2026-10-14 ("fourteen months in"), interleaved with about 140 unrelated travel and food
posts. The pottery photos progress with the date (one lumpy raw-clay bowl becomes a shelf of tall glazed pieces);
four posts are milestones and say so in their captions (2025-10-18, 2026-01-24, 2026-05-16, 2026-09-12). A second,
shorter run, their balcony garden (9 posts, 2026-04-05 to 2026-09-20), makes subject detection a real choice.
`liked-progress/` holds 12 progress posts they liked (seven left and right, three top and bottom, one four-up, one
single). The intended timeline is printed in the summary. It runs in well under 90 s.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX"
cp -r S "$SANDBOX/.claude/skills/transformation_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make a before and after of my pottery" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No music.** The export carries none and no music provider key is in the environment, so `music.py find` makes a
  bed in the mood of their music brief; `brief.md` and `storyboard.md` name the origin and the reason.

## Pass

The run ends in `build/<run stamp>/out/` (`build/RUN` names the run) with `film.mp4`, `then-now.png` (1080x1080),
`caption.md`, `review.html` and `brief.md`, and no square or 16:9 film and no story card, as the prompt asks for
none; the final reply names `build/<run stamp>/out/film.mp4` first; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the storyboard's
styleframes (`RUN/storyboards/drive/frames/`), `RUN/vote.md`, the timing round `RUN/critic/timing.json` and the cut
scores in `RUN/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,profile,r_frame_rate,duration -of csv RUN/out/film.mp4
```

shows h264 High 1080x1920 at 30/1 for at most 60 s and an aac track. `RUN/subject.json` names pottery, 2025-08-09 to
2026-10-14, "14 months", and the four milestones above; the film opens on the wall of dim tiles and dives to p01
(2025-08-09), and closes on the whole wall from it to the latest post (2026-10-14), ending on their handle. The 2 fps strip `RUN/qa/strip.png` is the film for the eye.

## The photo set

`TRANSFORMATION_PHOTOS=/path/to/set` puts a real photo set in place of the drawn pottery (the shape is in
`make_person.py --help`). With the pottery set the timeline is 27 posts from 2025-08-09 to 2026-10-14 ("fourteen months in"), with the four milestones above.
Run it the same way; the set is read as files and never written.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
