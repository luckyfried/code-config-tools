---
name: ig_year_in_review
description: "Makes a finished Instagram year in review: a 45-75 s vertical motion film of the person's year built from their own posts, reels, stories, likes and comments, in their style, plus a 10-card carousel, 3 story cards, a caption and a review page, saved to out/. Use for ANY request to recap someone's year on social media, however it is phrased: 'make my Instagram year in review', 'my year in review', 'Instagram wrapped', 'make me a wrapped', 'recap my year', 'my year on Instagram', '2026 recap reel', 'year recap video', 'yearly highlights', 'best of my year', 'top posts of the year', 'what did I post this year', 'my year in posts', 'a recap of my Instagram', 'year in review reel/carousel/post', 'Facebook year in review'. The person wants the finished film and cards, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, research their taste, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# Instagram year in review: the pipeline

Someone wants their year as a film they can post. Run **every movement below, in order, every time**. Each one
names the file to read and the commands to run; read the file, the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually
`.claude/skills/ig_year_in_review`). Shell variables do not survive between commands, so **write the path out in
full in every command**, for example `python3 .claude/skills/ig_year_in_review/scripts/qa.py gate`. Run every
command from the workspace root. Deliverables go in `out/`; everything else goes in `build/`.

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
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4` and the cards |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (their case, their length, no exclamation marks if they use none).
- Their photos carry the film. Never invent numbers: every number on screen comes from `build/stats.json`.
- Look at what you make: the style sheets, the frames and the cards, with the Read tool, before any score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste
  and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` opens everything), the idea of the film in a sentence, and that "do the second one" makes
  the runner-up.
