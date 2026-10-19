---
name: personal_brand_kit
description: "Makes a finished personal brand kit from the person's own Instagram feed: a 10-card swipeable style guide (1080x1350 PNGs: named palette, type, compositions, caption voice with three of their real captions, pillars with proportions, cadence, what their likes aspire to, what to stop, a one-line brand statement, the first week), a 20-30 s vertical reveal film, brand.json, a 30-day content plan in their voice, a caption and a review page, in out/, every finding measured from their posts and likes. Use for ANY request to find or define someone's style or brand from their feed: 'what's my style', 'define my aesthetic', 'make me a brand kit from my feed', 'personal brand kit', 'content style guide', 'brand guide from my posts', 'what should my feed look like', 'what are my content pillars', 'my palette from my feed', 'a content plan in my style'. The person wants the finished guide, film and plan, not advice: never answer with tips; invoke this skill and make them. Runs a fixed pipeline (gather, measure, three storyboards, a critic vote, Remotion production with generated clips, critic, gate, deliver) without asking questions."
---

# Personal brand kit: the pipeline

Someone wants to know their style and have it written down: a guide they can swipe, a film that reveals it, the
system as a file, and a month of posts in their voice. Here the research is the product: every card states what
was measured from their feed, with its number and an example of theirs. Run **every movement below, in order,
every time**. Each one names the file to read and the commands to run; read the file, the rules that matter live
there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the guide in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, the posts they like and save, your video model, your music
sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/personal_brand_kit`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/personal_brand_kit/scripts/qa.py gate`. Run every command from the workspace root.
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
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR] [--likes DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`; write `build/taste.md`, fix `build/taste.json`; `brand.py system`; `brand.py plan`, rewrite the captions, `brand.py plan` | taste.md, `build/brand.json`, `out/plan.md` |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/cards/` (10) |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Measured, never guessed: every share, color, time and device on a card comes from `build/brand.json`, which
  `research.py` measured from their posts and likes. Never invent a number or a caption; the three voice examples
  are their own captions.
- What the person says about their own brand (their bio, the request) wins over inference.
- Research comes first: nothing is drafted before `build/taste.md` and `build/brand.json` exist, and every word on
  screen and in the plan is in their voice (their case, their length, no exclamation marks if they use none).
- What to stop doing is said kindly: what those posts do, how they landed, never a judgment of the person.
- Look at what you make: the style sheets, the frames and the ten cards, with the Read tool, before any score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json`, `build/brand.json` or anything in `out/`; change the
  storyboard, `taste.json` or `build/plan.json` and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the guide
  and the film are (`out/review.html` opens everything), their brand in its one-line statement, that `out/plan.md`
  is the next 30 days, and that "do the second one" makes the runner-up film.
