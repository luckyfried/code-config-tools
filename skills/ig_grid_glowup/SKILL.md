---
name: ig_grid_glowup
description: "Gives an Instagram grid a finished makeover: a one-page audit of what the person's last 30 posts do as a grid and what their own likes and saves say works, the next nine posts as 1080x1350 images from their own photos shown over their real grid, a posting plan with captions in their voice, a drive film of about 20 seconds in three shapes (the reel, landscape and square), a Story card, the captions to copy, and a review page that opens on the film, saved to the run's out/. Use for ANY request to fix, plan or restyle someone's Instagram feed or grid: 'fix my grid', 'plan my next nine posts', 'grid makeover', 'glow up my grid', 'my feed looks messy', 'make my instagram cohesive', 'what should I post next', 'redesign my instagram grid', 'feed refresh', 'curate my feed'. The person wants the finished set, not advice: never answer with tips; invoke this skill and make it. Runs a fixed pipeline (gather, research, plan, three storyboards in three looks, vote and pick, music, render, critic, gate, deliver); the one question it may ask is which of the three looks they want."
---

# Instagram grid glow-up: the pipeline

Someone wants their grid to look better and their next nine posts planned. Run **every step below, in order, every
time**. Each one names the file to read and the commands to run; read the file, the rules that matter live there.

**Ask the person one thing at most: which of the three looks they want**, and only where `taste.json` says you may
(step 4). Everything else is a sensible assumption the scripts record in the run's `brief.md`; keep going. They can
redirect once they have the posts in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your music sources.

## Paths

`S` below means this skill's folder: the directory you read this SKILL.md from, written out in full. Every command
runs in a fresh shell, so no variable survives from one to the next: **write the path out in every command**, for
example `python3 /path/to/your/project/.claude/skills/ig_grid_glowup/scripts/qa.py check`. Run every command from the
workspace root.

Each run has a folder of its own, `build/<run stamp>/`: `gather.py` starts it and writes its name to `build/RUN`,
and every later script works inside the run `build/RUN` names (or the one `GG_RUN` names). Every file the steps name
(`taste.md`, `plan.json`, `out/film.mp4`) is in that folder, and the deliverables, and nothing else, are in its `out/`.
A rerun starts a new folder, so no run overwrites another. Paths you pass on the command line (`--photos`, `--pulled`)
are read from the workspace root.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks that this machine can make the film and installs nothing: Pillow, ffmpeg, the browser the films
render in and the built film composition. It prints what it found; when something is missing it says which, in one
sentence, and exits 1: tell the person that sentence and stop.

## The steps

| # | step | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, look at the grid, edit `audit.json`, `research.py audit`, write `taste.md` | `audit.md` (when there is a feed), taste.md with its five headings |
| 2 | plan | `S/pipeline/2-plan.md` | `plan.py draft`, write the captions, each post's shot and the film's hook, ask and world, `plan.py check` | `plan.md` |
| 3 | storyboards | `S/pipeline/3-board.md` | `storyboard.py draft`, `storyboard.py sheets`, look at each sheet | three storyboards, `out/boards.png` |
| 4 | vote and pick | `S/pipeline/4-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill the scores, `vote.py tally`; show `out/boards.png` and ask, or pick by taste; `storyboard.py pick <letter>` | `winner.json`, `board.json` |
| 5 | produce | `S/pipeline/5-produce.md` | `clips.py list`, `clips.py normalize`, `music.py find`, `music.py master`, `film.py render`, look | the three films, `out/posts/`, `out/story.png`, `out/caption.txt`, `out/grid-after.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (on FIX ONCE make the fix it names and run the steps it names, through round 2), `deliver.py` | green gate |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Their grid is the last 30 posts in posting order, three across, newest at the top left. Every number in the
  audit comes from their own likes and saves; never invent one.
- The film is their moments: each next post as the thing it shows them doing, where and with whom, in the words
  they posted with it, and their profile with the nine in place at the end. No post, like, save, follower count or
  date is ever on screen; a number appears only when it is a brag they would say out loud.
- Research comes first: nothing is planned before `taste.md` exists, and every word in a caption or the film is in
  their voice (their case, their length, no exclamation marks if they use none).
- The next posts are their own photos, the ones that never had a post of their own. When fewer than nine fit, the
  plan has fewer, and the film shows the posts it has.
- Look at what you make, with the Read tool, before any score: the grid sheet (when there is a feed), each storyboard's sheet, the posts,
  `out/grid-after.png` and the film's frames. Judge the posts against the real grid below them: they must look like
  a better version of this person's feed.
- Do not hand-edit `board.json`, a storyboard or anything in `out/`; change the plan or taste and run the step again.
- A film renders in chunks saved in the run. A render that was interrupted (the machine restarted, the session died)
  resumes when you run the same command again: finished chunks are kept and only the missing ones render. Never start
  over and never delete `render/chunks/`; a changed cut leaves its old chunks behind by itself. Run a render
  in the foreground in one tool call with a 40-minute timeout on that call, never in the background, and read its progress in `render/<name>.log`.
- The verdict is the run's own: on `FIX ONCE` you make the one fix it names in this run, render again and score
  round 2 before delivering; a film under the bar after that, or with no lever in the run, is delivered as the best
  cut with every score stated.
- Done means `deliver.py` printed `GATE GREEN`. Your reply then names the reel first: its full path from the project's
  root, exactly as deliver.py printed it on its last line, in a sentence ("Your reel is at
  build/20261026-014049/out/film.mp4"), never a bare `film.mp4`. Then, in two or three plain lines, that `review.html`
  in the same `out/` folder opens everything, what the film shows in a sentence, when the first post goes up, and
  that the two other looks are on that page: they can ask for one ("make the second one") and it is made in the same
  run (`S/pipeline/6-deliver.md`, Another look).
- A red gate is never a film to show: when deliver.py's last line says the gate failed, your reply says what failed
  and names no film, no path to one, and no review page.
