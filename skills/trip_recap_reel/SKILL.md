---
name: trip_recap_reel
description: "Makes a finished trip recap from the person's own posts, stories, photos and clips: a 30-60 s vertical motion film of one trip (1080x1920, day by day or place by place, with the route drawn as a map from their own geotags, their clips and generated establishing shots, cut to music), the same cut at 16:9 (1920x1080) for YouTube and desktop, five 1080x1920 story cards, a caption and a review page, saved to out/. Use for ANY request to turn a trip, a holiday or a vacation into a video, however it is phrased: 'recap my trip', 'trip recap', 'travel recap', 'make a travel reel from these', 'make a travel video', 'our Lisbon week as a video', 'my Japan trip as a reel', 'vacation video from my posts', 'holiday video', 'make a reel of our honeymoon', 'turn my trip photos into a video', 'a recap of last weekend in Paris', 'travel montage', 'road trip video', 'recap of my summer trip', 'a reel of my last trip', 'make something from my travel photos'. The person names a trip by place, dates, album or folder, or names none and gets the most recent trip. They want the finished films and cards, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, find the trip and research their travel taste, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# Trip recap reel: the pipeline

Someone wants a trip as a film they can post. Run **every movement below, in order, every time**. Each one names
the file to read and the commands to run; read the file, the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/trip_recap_reel`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/trip_recap_reel/scripts/qa.py gate`. Run every command from the workspace root.
Deliverables go in `out/`; everything else goes in `build/`.

## Which trip

Pass what the person named to `research.py`, in their words: `--place "lisbon"`, `--from 2026-10-03 --to
2026-10-08`, `--album "lisbon week"`, or `--folder DIR` (and `gather.py --photos DIR` for a folder of clips they
pointed at). Their words win over anything the data suggests. With nothing named, the most recent trip is used and
the brief says so.

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
| 1 | research | `S/pipeline/1-research.md` | `research.py [--place ... / --from ... --to ... / --album ... / --folder ...]`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/film-16x9.mp4`, `out/story-1.png` .. `out/story-5.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The trip is theirs: its days, places and people come from their own dates, geotags, captions and folder names
  (`build/trip.json`), and every place in it appears in the film. Never invent a place, a date or a person.
- The map is drawn from their coordinates in their palette; no map tiles are fetched from any service.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (their case, their length, no exclamation marks if they use none). Their travel style (the trip's palette,
  light and pace, which `research.py` measures against their everyday posts) leads the film's look.
- One storyboard makes both films; the 16:9 cut is the same beats laid out for a wide frame.
- Look at what you make: the style sheets, the frames of both films and the five story cards, with the Read tool,
  before any score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste
  and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the films
  are (`out/review.html` opens everything), the idea of the film in a sentence, and that "do the second one" makes
  the runner-up.
