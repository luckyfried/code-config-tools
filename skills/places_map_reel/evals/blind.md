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

writes one invented person, Maren Okafor (@maren.okafor), who lives in Lisbon and went to eleven places in 2026: an
Instagram export in the JSON layout (posts, reels and stories, most of them geotagged, likes across 40 accounts,
saves, comments, followers and following, per-post insights, media), a small Facebook export (posts, check-ins and
albums), photos warm away from home and cool at home (some named `.heic` that are JPEG inside), and three short mp4
reels shot in Porto, Seville and Oaxaca. Coimbra and Córdoba are named only in captions; Porto and Seville were
visited twice; Oaxaca is the one far trip. With `--set DIR` it also copies a set of photographs of the eleven places
(a folder per place, each with its `manifest.json`) to `photos-of-the-year/`, the photographs they hand over beside
the exports, and every post and story photograph of a place the set holds is one of the set's own photographs of it,
so the film shows real photographs and never the fixture's drawings; the agent reads it with `research.py --set photos-of-the-year`. It prints the intended place list
(`intended_places`) and runs in a few seconds.

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
- **No music.** The export carries none, so `music.py find` makes a bed from the picked look's recipe, steered by the person's
  music brief; `brief.md` names the origin.

## Pass

The run ends with a green gate: `python3 S/scripts/qa.py gate` prints `GATE GREEN`, and the run's folder
(`build/<run stamp>/`, named in `build/RUN`) holds `out/film.mp4`, `out/film-16x9.mp4`, `out/film-square.mp4`,
`out/post.png`, `out/story.png`, `out/caption.md`, `out/boards.png` and `out/review.html` and nothing else in `out/`; `brief.md` beside
`out/`; the three looks' sheets (`storyboards/<style>/sheet.png`), `vote.md` and the cut scores in `critic/`. The places in
`brief.md`'s table are the fixture's `intended_places`, eleven, and the caption says 11. The film at 2 fps for the eye
is `qa/film-strip2.png`, which `film.py render` writes through its last step, `qa.py check`.

## Judging

Every film, with and without the kit, is judged on the seven criteria in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
