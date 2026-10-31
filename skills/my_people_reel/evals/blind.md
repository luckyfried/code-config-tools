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
accounts, saves, the posts others tagged the account in, the comments the account wrote and the comments others wrote on its posts,
followers and following, per-post insights, media), a small Facebook export (posts and albums), photos in one
palette, and short mp4 reels. The account's people are six recurring accounts with clearly different volumes, each the one
the account is with most in one stretch of the year; eleven group photos and two short group reels tag several of them at
once; their comments come in six distinct voices; one of them (liv.outside) is tagged most of all and never
comments, so tags alone give the wrong order. The intended order, every tag and comment counted once, is dani.reyes
110, theo.makes 78, ines.walks 72, then kofi.cooks and liv.outside level at 43 (the handle breaks the tie; then
sam_and_june, far below). It runs in a few seconds.

A second person proves the design belongs to the kit and not to Maren's photographs:

```
python3 S/evals/fixtures/make_seed_person.py SANDBOX PHOTOS
cd SANDBOX && python3 S/scripts/gather.py --pulled pulled
```

writes Noor Haddad (@noor.haddad, Lisbon), built from a folder of real CC0 photographs named by subject (PHOTOS, read
only), as the items an agent pulls from a connected account: the account's own people, dates, captions and counts, the intended
order tomas.surf, joana.lima, rita.clay, lena.reads, ze.do.largo. It runs through the same steps from gather to
deliver.

Both fixtures write every caption from the photograph it is posted with. A caption that names what its photograph
does not show (hills over a beach) is a defect in the fixture: fix the caption at its cause, in the fixture's script,
never by swapping the photograph or the line on the board to hide it.

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
MCP config leaves the agent with no Instagram or browser tool, which is the case this run proves. The
without-kit run is the same command in a sandbox with the fixture and no `.claude/skills/`.

## What the agent has, and what the kit does about it

- **No Instagram or Facebook account, no signed-in browser.** gather.py records both doors closed and opens the
  export door; `brief.md` lists all of them.
- **No music.** The export carries none, so `music.py find` makes the bed from their music brief; `brief.md`
  names the origin.

## Pass

The run ends in its run folder `R` (`build/<run stamp>/`, named in `build/current`) with `R/out/film.mp4` and no
square film, wide film or story cards (the request asked for a video), `R/out/caption.md` tagging every one of them,
`R/out/review.html`, `R/out/cover.png`, `R/out/story.png`, `R/out/boards.png` and the other two looks in `R/out/looks/` and nothing else in `R/out/` but the reel, with `R/brief.md` beside it; the agent's reply names the reel first by the path deliver.py printed last
(`build/<run stamp>/out/film.mp4`); `python3 S/scripts/qa.py gate` prints `GATE
GREEN`; the three looks' sheets (`R/storyboards/<style>/sheet.png`), `R/out/boards.png`, `R/vote.md`, `R/winner.json`
and the cut scores in `R/critic/` exist; `R/people.json` ranks the five in the intended order; and

```
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate,duration -of csv "build/$(cat build/current)/out/film.mp4"
```

shows h264 1080×1920 at 30/1 for 30–60 s and an aac track. The beats at rest for the eye are in `R/frames/`.

## Judging

Every film, with and without the kit, is judged on the six scored rules in `S/critic/critic.md` by eye: the frames,
the sheets, the film.
