---
name: month_in_review_stories
description: "Makes a finished Instagram month in review as stories: a numbered series of three to five 1080x1920 story cards (one idea each, every card both a static PNG and a 15 s animated story with music), one 15 s story film, a caption, a template.json that keeps next month's series matching, and a review page, saved to out/. The month is the one the person names; otherwise the last full month. Use for ANY request to recap someone's month as stories, however it is phrased: 'my month in review', 'month in review stories', 'October recap stories', 'september recap', 'make my september recap stories', 'monthly wrap-up', 'my monthly wrap up for instagram', 'what I posted this month as stories', 'month recap', 'recap my month', 'last month in stories', 'a story series of my month'. The person wants the finished stories, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, research the month against their year, three storyboards with style sheets, a three-critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# Month in review stories: the pipeline

Someone wants their month as a set of Instagram stories they can post tonight: a numbered series of story cards,
one idea per card, each animated and still, and one 15 s story film. Run **every movement below, in order, every
time**. Each one names the file to read and the commands to run; read the file, the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the stories in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually
`.claude/skills/month_in_review_stories`). Shell variables do not survive between commands, so **write the path out
in full in every command**, for example `python3 .claude/skills/month_in_review_stories/scripts/qa.py gate`. Run
every command from the workspace root. Deliverables go in `out/`; everything else goes in `build/`.

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
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--month M] [--pulled DIR] [--photos DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its six headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three style sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/cards/` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film and the cards place them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The month is the one they named (pass it as `--month`); otherwise the last full month. It is always set against
  their year: the twelve months that end with it.
- Every number on screen is theirs, from `build/stats.json` and `build/research.json`. The three that hit are their
  three most-liked posts of the month by their own counts; never swap one in by taste, never invent a number.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (their case, their length, no exclamation marks if they use none).
- Three to five cards, one idea per card, numbered as a series. Each card is 15 s animated and has a static PNG
  drawn from the same storyboard.
- Look at what you make: the style sheets and the frames, with the Read tool, before any score.
- A clip that did not arrive is substituted with an animated photo of theirs, never left as a gap; `brief.md`
  says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste and
  run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the
  stories are (`out/review.html` opens everything), the idea of the series in a sentence, the order to post the
  cards, and that "do the second one" makes the runner-up.
