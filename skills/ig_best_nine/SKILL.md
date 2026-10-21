---
name: ig_best_nine
description: "Makes a finished Instagram best nine: a 15-30 s motion film of the person's nine most-liked posts of the year (ranked by their own likes, ties broken by comments then recency) in three shapes (1080x1920 for reels and stories, 1080x1080 for the feed, 1920x1080 wide), the classic 1080x1080 best-nine image, one 1080x1920 story card, a caption and a review page, from their own photographs. Use for ANY request for someone's most-liked or top posts of the year, however it is phrased: 'my best nine', 'best nine', 'make my best nine', 'top nine', 'my top 9', '2026 best nine', 'best nine video', 'my most liked posts this year as a video', 'my most liked posts of the year', 'my top posts this year', 'my nine most popular posts', 'top 9 grid', 'best of my grid', 'my most popular instagram posts as a reel', 'top nine reel/collage/story'. The person wants the finished film, the wall and the card, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, research their taste and why the nine worked, a storyboard built from their numbers, a critic vote with the swap test, the timed cut read for monotony, Remotion studio render, critic, gate, deliver) without asking questions."
---

# Instagram best nine: the pipeline

Someone wants their nine most-liked posts of the year as a film, a wall and a story they can post. Run **every
movement below, in order, every time**. Each one names the file to read and the commands to run; read the file,
the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in the run's
`out/brief.md`, and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your music sources.

## Paths and runs

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/ig_best_nine`).
Shell variables do not survive between commands, so **write the paths out in full in every command**. Run every
command from the workspace root.

Every run is one folder, `build/<UTC stamp>/`, which `gather.py` makes and prints as `run: build/<stamp>`. Every
later command takes it as `--run build/<stamp>` and writes only inside it; the deliverables land in its `out/`. A
new gather is a new run, so nothing a person was given is ever overwritten.

**Their photographs.** The setting `BEST_NINE_PHOTOS` names the folder their photographs live in (or pass
`gather.py --photos DIR`). Gather finds each post's photograph there by its file name first, then in the download
itself; with neither, the download's own media is used. A year with fewer than nine posts makes a film of the
posts it has: the storyboard lays them out, and the film is shorter.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` finds or installs Pillow (a venv in the skill folder when pip is locked), ffmpeg, node (a portable one
under `S/.cache/` when there is none) and the Remotion studio's packages and browser, all inside the skill folder.
The first run takes a minute or two; later runs take a second. The render uses the graphics card when the machine
has an NVIDIA one and the processor otherwise; the films are the same either way.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py [--door ...] [--pulled DIR] [--photos DIR]` | `run: build/<stamp>` printed |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write `taste.md` and fix `taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `storyboard.py check`, `storyboard.py sheets`, look | the sheet, zero findings |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores and the swap test, `vote.py tally` | `winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed` and the read, `qa.py timed`, `music.py master`, `film.py render` | `out/film.mp4` and its two other shapes, `out/best-nine.png`, `out/story.png` |
| 5 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py ... --run build/<stamp>` (gather and setup take no run); each answers
`--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The nine are theirs by their own numbers: posts and reels of the year ranked by likes, ties broken by comments,
  then by the newer post. Never swap one in by taste; never invent a number. Every number on screen comes from the
  run's `stats.json`.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen is in their voice
  (`taste.json` `words.<tone>`: their case, their length, no exclamation marks if they use none).
- The storyboards are computed from their numbers and photographs: each tone's builder places every photograph by
  its focus point and square crop, and the bounds check refuses a board where, at rest, a photograph is cropped by
  the frame, sits behind another, loses its gutter, or a tag hides a count. Change the words or the taste, never
  the board by hand.
- Look at what you make: the style sheets, the timed cut's strip, the frames, the best-nine image and the story
  card, with the Read tool, before any score or read.
- Do not hand-edit `film.json`, the boards or anything in `out/`; change the words or the taste and run the step
  again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` in the run opens everything) and the idea of the film in a sentence.
