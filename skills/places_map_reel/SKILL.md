---
name: places_map_reel
description: "Makes a finished travel map of someone's year: a 30-60 s vertical motion film that travels through every place they went this year in the order they went (a map drawn in their colors, their photos pinned to it as the route grows), a 1080x1350 map poster of all the year's places, a caption that states how many places, and a review page, saved to out/. Use for ANY request to show where someone went this year, however it is phrased: 'a year of places', 'everywhere I went this year', 'my travel map video', 'all the cities I visited as a video', 'map of my year', 'where I went in 2026', 'my year in places', 'my travel year as a reel', 'the places I visited this year', 'a map of all my trips', 'travel recap of the year', 'every city I went to this year', 'my 2026 travel map', 'places I've been this year', 'make a map reel of my travels', 'route of my year', 'where did I go this year, as a video'. The person wants the finished film, the poster and the caption, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, find the places from geotags, captions and folder names, research their taste, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# A year of places: the pipeline

Someone wants every place they went this year as a film, a map poster and a caption they can post. Run **every
movement below, in order, every time**. Each one names the file to read and the commands to run; read the file,
the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands. When they name a year, pass it to `gather.py`
as `--year`; otherwise the kit takes their latest year with enough posts, which is this year for anyone who posts.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/places_map_reel`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/places_map_reel/scripts/qa.py gate`. Run every command from the workspace root.
Deliverables go in `out/`; everything else goes in `build/`.

## Start

```
python3 S/scripts/setup.py
mkdir -p out build
```

`setup.py` finds or installs Pillow (a venv in the skill folder when pip is locked), ffmpeg, node (a portable one
under `S/.cache/` when there is none) and the Remotion project's packages and browser. The first run takes a minute
or two; later runs take a second. It prints `"engine": "remotion"`, or `"stills"` when node cannot run here.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, check `build/places.json`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/poster.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The places are theirs: geotags first, then places named in their captions and folder names, merged into one
  list in the order they went. A place visited twice counts once. Their own words about where they went win over
  inference: when they say where home is or name a place, `build/places.json` follows them.
- The map is drawn by the kit from the places' coordinates over the land shapes it ships (public domain). Never
  fetch map tiles or a satellite image from any service.
- Every place is in at least one beat of the film, and the caption's count is the count of places.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (their case, their length, no exclamation marks if they use none).
- Look at what you make: the style sheets, the frames and the poster, with the Read tool, before any score.
- A clip that did not arrive is substituted with an animated treatment of their photo, never left as a gap;
  `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard, the places
  or taste and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` opens everything), the idea of the film in a sentence, and that "do the second one" makes
  the runner-up.
