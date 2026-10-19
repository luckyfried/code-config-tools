---
name: transformation_reel
description: "Makes a finished before-and-after: a 30-60 s vertical motion film of one subject the person has posted over time (their pottery, a renovation, a garden, their art, their training, themselves), from the subject's first dated post to its latest, every photo dated and in order with the milestones marked, plus a 1080x1350 then/now card (the first and the latest side by side with the span between them), a caption that states the span, and a review page, saved to out/. Use for ANY request to show how something of theirs changed over time, however it is phrased: 'before and after', 'make a before and after of my pottery', 'my progress video', 'progress reel', 'a year of my art', 'a year of my home', 'my renovation before and after', 'my garden over the year', 'my fitness journey as a video', 'my transformation', 'glow-up reel', 'glow up video', 'then and now', 'how far I've come', 'day 1 vs now', 'my journey reel', 'timelapse of my progress'. The person may name the subject or not; when they name nothing the kit finds the subject their feed tracks longest. The person wants the finished film, the card and the caption, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, research the subject's timeline and their taste, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# Transformation reel: the pipeline

Someone wants to show how one thing of theirs changed: a before and after, a progress video, a glow-up. Run
**every movement below, in order, every time**. Each one names the file to read and the commands to run; read the
file, the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, a folder of progress posts they liked, your video model, your
music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/transformation_reel`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/transformation_reel/scripts/qa.py gate`. Run every command from the workspace root.
Deliverables go in `out/`; everything else goes in `build/`.

## Start

```
python3 S/scripts/setup.py
mkdir -p out build
```

`setup.py` finds or installs Pillow (a venv in the skill folder when pip is locked), ffmpeg, node (a portable one
under `S/.cache/` when there is none) and the Remotion project's packages and browser. The first run takes a minute
or two; later runs take a second. It prints `"engine": "remotion"`, or `"stills"` when node cannot run here.

## The subject

When the person names it ("my pottery", "the kitchen", "my garden", "me"), pass their words to research:
`research.py --subject "my pottery"`. When they name nothing, run `research.py` with no subject: it picks the
subject with the longest dated run of posts and says which runs it weighed in `build/subject.json`.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR] [--likes DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py [--subject "their words"]`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/then-now.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The timeline is theirs: every photo on screen is one of the subject's posts, dated as they posted it, and the
  photos run oldest to latest. The film opens its photos on the subject's first dated post and ends them on its
  latest; the then/now card and every split pair the same two. `storyboard.py check` and the gate refuse anything
  else.
- Their own words about what changed win over anything inferred from the photos: a caption that says "milestone",
  "first", "finally" marks a milestone before any measured change does.
- The span is the time between the first post and the latest (`build/subject.json` `span`), and the caption says
  it in those words.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (their case, their length, no exclamation marks if they use none).
- Look at what you make: the style sheets, the frames and the then/now card, with the Read tool, before any score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste and
  run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` opens everything), the span it covers, the idea of the film in a sentence, and that "do the
  second one" makes the runner-up.
