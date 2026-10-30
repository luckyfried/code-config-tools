---
name: ig_best_nine
description: "Makes a finished Instagram best nine: a motion film of the person's nine top posts of the year, ranked by their own likes, comments and saves (the nine most recent when the data carries none), counting down from the ninth to the first and ending on the nine as a 3x3 grid. Delivers a 1080x1920 reel at the length they ask (20 to 45 s, 30 s when they name none), the classic 1080x1080 best-nine image, a caption and a review page; a square or wide film and a story card only when asked. Made in one of three looks they pick from a sheet. Use for ANY request for someone's most-liked or top posts of the year: 'my best nine', 'top nine', 'my top 9', '2026 best nine', 'best nine video', 'my most liked posts of the year', 'my top posts this year', 'top 9 grid', 'best of my grid', 'top nine reel'. The person wants the finished film, not advice: invoke this skill and make it."
---

# Instagram best nine

Someone wants their nine most-liked posts of the year as a film, a best-nine image and a caption they can post. Run
**every movement below, in order, every time**. Each one names the file to read and the commands to run; read the
file, the rules that matter live there.

Ask at most one question, the look (movement 3), and only where you may ask. For everything else make the sensible
assumption, let the scripts record it in the run's `brief.md`, and keep going. They can redirect once they have the
film.

**Use anything you already have access to**: their connected Instagram and Facebook accounts, a signed-in browser,
an export, their photo folders, your music sources.

## Paths and runs

`S` below is the folder this SKILL.md was read from. Every command runs in a fresh shell, so nothing set in one
command (a variable, a `cd`) reaches the next: **write every path out in full in every command**, and run every
command from the workspace root.

Every run is one folder, `build/<UTC stamp>/`, which `gather.py` makes and prints as `run: build/<stamp>`. Every
later command takes it as `--run build/<stamp>` and writes only inside it; the deliverables land in its `out/` and the
brief beside it. A new gather is a new run, so nothing a person was given is ever overwritten.

**Their photographs.** The setting `BEST_NINE_PHOTOS` names the folder their photographs live in (or pass `gather.py
--photos DIR`). A best nine is nine: a year with fewer than nine posts with a photograph makes nothing, and the step
prints `not delivered: <n> posts, nine needed`; tell the person that sentence and stop.

**The length.** The reel runs the length they asked for, from 20 to 45 s, and 30 s when they named none: write it in
`taste.json` `seconds` in movement 1. A length outside 20 to 45 s makes nothing and prints `not made: ...`; tell them
that sentence and stop.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` makes ready everything the film needs and keeps it under `~/.cache/code-config/ig_best_nine/`; the first
run takes a minute or two, later runs a second. It prints what it found and `"ok": true`; when it does not, tell the
person the line it printed and stop.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py [--door ...] [--pulled DIR] [--photos DIR]` | `run: build/<stamp>` printed |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write `taste.md` and fix `taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `check`, `sheets`, look at `out/boards.png` | three looks, zero findings |
| 3 | the look | `S/pipeline/3-vote.md` | ask which look (or pick by taste), `vote.py pick --board B` | `winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find`, `storyboard.py snap`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed` and the read, `qa.py timed`, `music.py master`, `film.py render` | `out/film.mp4`, `out/best-nine.png` |
| 5 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py ... --run build/<stamp>` (gather and setup take no run); each answers
`--help` with its inputs, outputs and options. If `gather.py` exits 3, every door is closed: tell the person the one
sentence it printed and stop.

## The look

`storyboard.py sheets` writes `out/boards.png`: the same film in three looks, A, B and C, each by its hook, a middle
beat and its closer, with its name and a sentence.

- **Where you may ask** (`taste.json` `ask` is `true`): show them `out/boards.png` and ask "Which look do you want: A,
  B or C?" Run `vote.py pick --board <their answer>`.
- **Where nothing may be asked** (`ask` is `false`): pick by `taste.md` and say why in one line: `vote.py pick
  --board <look> --why "<one line>"`.

After delivery the review page offers the other two. When they say "make the second one" (or name a look), run `vote.py
pick --board <that look>` in the same run, then movement 4 from `music.py find` and movement 5 through `deliver.py`.

## Rules that win

- The nine are theirs by their own numbers: likes first, then comments, then saves, then the newer post. Never swap
  one in by taste. The numbers pick the nine and never reach the screen: the film counts down from the ninth to the
  first with no number on screen, each as the moment it was, with their own caption line (a post without one is
  wordless), and ends on the nine as a three by three grid, the first at its top left.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen is in their voice.
- The storyboards are computed from their photographs, captions and dates. Change the words, a beat's lever or the
  taste, never a board, `film.json` or anything in `out/` by hand.
- Look at what you make, with the Read tool, before any score or read: the sheets, the timed cut's strip, the frames,
  the best-nine image.
- The film ships at the bar: the critics' mean 4.5 or more with no criterion under 4. Under it, the one fix; still
  under it, the best cut is delivered with its scores in the run's `brief.md`. Scores never appear on the review page.
- Make what they asked for: the reel, the best-nine image and the caption. The square and wide films and the story
  card render only when they ask for them (`film.py render --also landscape square stories`, naming only those).
- Run `film.py preview` and `film.py render` in the foreground in one tool call with a 40-minute timeout, never in
  the background; read their progress in `render/preview.log` and `render/film.log`. An interrupted render resumes
  when the same command runs again; never delete `render/chunks/`.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, first where the
  reel is, its full path from the workspace root copied from the last line `deliver.py` printed ("Your reel is at
  build/20261026T014049Z/out/film.mp4", never the bare `film.mp4`), then that `out/review.html` in the run opens
  everything, then the ranking `deliver.py` printed above the path, the look and the idea of the film in a sentence,
  and that they can say "make the second one" for another look.
- A gate that has not passed ends `deliver.py` on `not delivered: the gate failed on ` and the failing checks' names,
  with no path: fix them and deliver again, and if you stop there, say what failed and name no film and no path.
