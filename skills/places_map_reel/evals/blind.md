# Blind run

A fresh agent, a synthetic person, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate.

## Trigger phrasings

Any one of these, typed as the whole request:

- make a video of everywhere I went this year
- my travel map video
- all the cities I visited as a video
- map of my year
- a year of places

## The fixture

```
python3 S/evals/fixtures/make_person.py SANDBOX
```

writes one invented person, Maren Okafor (@maren.okafor), who lives in Lisbon and went to eleven places in 2026:
an Instagram export in the JSON layout (posts, reels and stories, most of them geotagged, likes across 40 accounts,
saves, comments, followers and following, per-post insights, media), a small Facebook export (posts, check-ins and
albums), photos warm away from home and cool at home (some named `.heic` that are JPEG inside), and three short mp4
reels shot in Porto, Seville and Oaxaca. Coimbra and Córdoba are named only in captions; Porto and Seville were
visited twice; Oaxaca is the one far trip. It prints the intended place list (`intended_places`) and runs in a few
seconds.

## The run

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills" && python3 S/evals/fixtures/make_person.py "$SANDBOX" > "$SANDBOX/../fixture.json"
cp -r S "$SANDBOX/.claude/skills/places_map_reel"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "make a video of everywhere I went this year" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

Keep the fixture's printout outside the sandbox: it names the intended places, and the agent must find them on its
own. `--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with
no MCP config leaves the agent with no Instagram, browser or video tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No video model.** The agent generates nothing and runs `clips.py normalize --why "no video model in this
  session"`: every clip of the winning board is substituted with an animated treatment of one of their photos,
  a clip of their own reels stays as it is, and `brief.md` says which clips were substituted and why. The
  generated-clip path is proven by hand instead: copy one or two of the fixture's reels
  (`instagram-*/media/reels/*.mp4`) to `build/clips/01.mp4` and `02.mp4` as stand-ins for the model's output and
  run `clips.py normalize`; they arrive as "generated".
- **No music.** The export carries none, so `music.py find` exits 3 and `music.py make` writes the bed; `brief.md`
  names the origin.

## Pass

The run ends with `out/film.mp4`, `out/poster.png` (1080×1350), `out/caption.md`, `out/review.html` and
`out/brief.md`; `python3 S/scripts/qa.py gate` prints `GATE GREEN`; the three style sheets
(`build/storyboards/N/sheet.png`), `build/vote.md` and the cut scores in `build/critic/` exist; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv out/film.mp4
```

shows h264 1080×1920 at 30/1 for 30–60 s and an aac track. The places in `out/brief.md`'s table are the
fixture's `intended_places`, eleven, and the caption says 11. Then one frame per beat for the eye:
`python3 S/scripts/film.py frames --out frames`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
