---
name: ig_grid_glowup
description: "Gives an Instagram grid a finished makeover: a one-page audit of what the person's last 30 posts are doing as a grid (palette, crops, spacing, rhythm) and what their own likes and saves say works, the next nine posts designed as 1080x1350 images from their own photos and shown in place over their real grid, a posting plan with nine captions in their voice and an order, a 15 s before-and-after vertical film, and a review page with three grid directions and the vote, saved to out/. Use for ANY request to fix, plan, clean up or restyle someone's Instagram feed or grid, however it is phrased: 'fix my grid', 'make my feed look better', 'plan my next nine posts', 'plan my next 9', 'grid makeover', 'grid glow-up', 'glow up my grid', 'my feed looks messy', 'my grid is a mess', 'make my instagram cohesive', 'give my feed an aesthetic', 'what should I post next so my grid looks good', 'redesign my instagram grid', 'feed refresh', 'curate my feed', 'make my profile look professional'. The person wants the finished audit, posts, plan and film, not advice: never answer with tips or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, read the grid and their taste, three grid directions, a critic vote, the plan, Remotion production with generated clips, critic, gate, deliver) without asking questions."
---

# Instagram grid glow-up: the pipeline

Someone wants their grid to look better and their next nine posts planned. Run **every movement below, in order,
every time**. Each one names the file to read and the commands to run; read the file, the rules that matter live
there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the posts in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your image and video models, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/ig_grid_glowup`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/ig_grid_glowup/scripts/qa.py gate`. Run every command from the workspace root. Deliverables
go in `out/`; everything else goes in `build/`.

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
| 1 | research | `S/pipeline/1-research.md` | `research.py`, look at the grid, edit `build/audit.json`, `research.py audit`, write `build/taste.md` | `out/audit.md`, taste.md with its five headings |
| 2 | directions | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, stills, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | plan, produce | `S/pipeline/4-produce.md` | `plan.py draft`, write nine captions, `plan.py check`, `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/posts/`, `out/grid-after.png`, `out/plan.md`, `out/film.mp4` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Their grid is the last 30 posts in posting order, three across, newest at the top left. Every number in the
  audit comes from their own likes and saves; never invent one.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word in a post, a caption or
  the film is in their voice (their case, their length, no exclamation marks if they use none).
- The nine are made from their own photos. Where no photo of theirs fits a spot, a generated still in their palette
  stands in, and the plan says which post it is.
- Look at what you make, with the Read tool, before any score: the grid sheet, the three style sheets, the nine
  posts, `out/grid-after.png` and the film's frames. Judge the nine against the real grid below them: they must
  look like a better version of this person's feed.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard, the plan or
  taste and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where
  everything is (`out/review.html` opens it all), the direction in a sentence, when the first post goes up, and that
  "do the second one" makes the runner-up direction.
