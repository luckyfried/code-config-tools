---
name: my_people_reel
description: "Makes a finished film of the people someone spent the year with: a 30-60 s vertical motion film of their people (ranked from who they tag, who tags them, who they @mention, and who comments on whose posts, every signal counted together; their own list wins when they name people), one 1080x1920 story card per person (that person's best photo and a line of their comments), a caption that tags every one of them, and a review page, saved to out/. Use for ANY request for a film, reel, recap or post about the people in someone's year, however it is phrased: 'who I spent the year with', 'my people', 'my people 2026', 'friendship recap', 'the friends who made my year', 'my top friends as a video', 'my top friends of 2026', 'best friends recap', 'who I hung out with most', 'a reel of my friends from this year', 'my favorite people of the year', 'friends of the year video', 'shout out my people', 'tag my friends in a year recap', 'my crew this year'. The person wants the finished film, the cards and the caption, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. Runs a fixed pipeline (gather everything you can reach, research who their people are, each one's best photo, line and stretch of the year, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# My people: the pipeline

Someone wants a film of the people who made their year, with a story card for each of them and a caption that tags
them all. Run **every movement below, in order, every time**. Each one names the file to read and the commands to
run; read the file, the rules that matter live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually `.claude/skills/my_people_reel`).
Shell variables do not survive between commands, so **write the path out in full in every command**, for example
`python3 .claude/skills/my_people_reel/scripts/qa.py gate`. Run every command from the workspace root. Deliverables
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
| 1 | research | `S/pipeline/1-research.md` | `research.py [--people a,b,c] [--top N]`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/people/NN-<handle>.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Their people are theirs by their own words first: when the request names people ("me, Dani and Theo", "my
  roommates @a and @b"), pass them to `research.py --people a,b,c` in the order given and never add or drop one.
  Otherwise the order is the count in `build/people.json` (five people unless they asked for a number: `--top N`).
  Never swap someone in by taste; never invent a number. Every number on screen comes from `build/people.json`.
- Each person's line is theirs: a comment they wrote, or, for someone who never comments, the person's own caption
  about them. You may pick a different one of their lines from `build/people.json`; never write one for them.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in the
  person's voice (their case, their length, no exclamation marks if they use none).
- Every person is in the film at least once and has a story card; the caption tags every one of them.
- Look at what you make: the style sheets, the frames and every story card, with the Read tool, before any score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste
  and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` opens everything), who is in it and in what order, the idea of the film in a sentence, and
  that "do the second one" makes the runner-up.
