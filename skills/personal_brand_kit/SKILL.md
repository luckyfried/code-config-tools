---
name: personal_brand_kit
description: "Makes a finished personal brand kit from the person's own Instagram feed: a 12-30 s film of their story told in their own photographs and caption lines, in the look they pick from three (kinetic type, editorial quiet, swiss grid, or a look they name), as a vertical reel with its square and wide films, a story card and an image to post (a carousel of stills when they ask for one), brand.json (named palette with shares, type, caption voice with their real captions, pillars with proportions, cadence, what their likes aspire to, what to stop, a one-line brand statement), a 30-day content plan in their voice, a caption and a review page, in out/, every finding measured from their posts and likes. Use for ANY request to find or define someone's style or brand from their feed: 'what's my style', 'define my aesthetic', 'what should my feed look like?', 'make me a brand kit from my feed', 'turn my feed into a brand guide', 'a content style guide', 'personal brand kit', 'what are my content pillars', 'my palette from my feed', 'a content plan in my style'. They want the finished film, system and plan, not advice: never answer with tips; invoke this skill."
---

# Personal brand kit: the pipeline

Someone wants to know their style and have it written down: a film that shows it, the system as a file, and a month
of posts in their voice. Here the research is the product: the system is measured from their feed, with its numbers
and an example of theirs, and the film tells their story in their own photographs and their own caption lines. Run
**every movement below, in order, every time**. Each one names the file to read and the commands to run; read the
file, the rules that matter live there.

**One question, and only one: which look.** The film is drafted in three looks and the person picks one from
`out/boards.png`. Everything else is a sensible assumption the scripts record in the run's `brief.md`. When
`taste.json` `ask` is false (they said "just make it", or the session cannot ask), pick the look by their taste and
give the reason in one line (`vote.py pick <letter> --why "..."`).

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, the posts they like and save, your music sources.

## Paths

`S` below means this kit's folder: the folder you read this SKILL.md from, wherever that is. Every command runs in a
fresh shell, so **write the path out in full in every command**, for example
`python3 /path/to/personal_brand_kit/scripts/qa.py gate`, and run every command from the workspace root. A variable
set in one command is gone in the next.

Every run writes into its own folder, `build/<run stamp>/`: `gather.py` starts it and names it in `build/run`, and
every other script works inside the run `build/run` names. Every file the movements name (`taste.md`, `brand.json`,
`storyboards/`, `cut.mp4`) is in that folder, and `out/` inside it holds the deliverables. A new run never touches an
earlier one. The render's own scratch (frames, the browser's profile) lives under `~/.cache/code-config/personal_brand_kit/`.

**Their photographs** are their posts' own pictures. When the person names a folder of their photographs to use
instead (their camera roll, an edit they made), set `BRAND_PHOTOS` to it on `storyboard.py draft`; the film then
casts its photographs from that folder.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for what a film needs and installs nothing: a python3 with Pillow, ffmpeg, a Chromium browser and
the kit's built film composition (`S/motion/dist/`, which ships with the kit). It prints what it found with `"ok":
true`; when something is missing it says what, in a plain sentence, and exits 1. Tell the person that sentence.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR] [--likes DIR]` | `library.json` in a new run |
| 1 | research | `S/pipeline/1-research.md` | `research.py`; write `taste.md`, fix `taste.json`; `brand.py system`; `brand.py plan`, rewrite the captions, `brand.py plan` | `taste.md`, `brand.json`, `out/plan.md` |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`; `storyboard.py check`; `storyboard.py sheets`, look at `out/boards.png` | three looks, each in bounds, and `out/boards.png` |
| 3 | vote and pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`; show `out/boards.png` and ask which look; `vote.py pick <letter>` | `winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find`, `storyboard.py snap`, `music.py master`, `film.py cut` | `cut.mp4` and its strips |
| 5 | critic | `S/pipeline/5-critic.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told) | `critic/verdict.json` ships the cut or spends its fix |
| 6 | render, deliver | `S/pipeline/6-deliver.md` | `film.py render`, write `caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Another look after delivery

When the person, after seeing the film, says "make the second one" (or names another look), make it in the same
run, without asking anything else: `vote.py pick <letter>` (it clears the old look's music, cut and rounds), then
`music.py find`, `storyboard.py snap`, `music.py master`, `film.py cut`, `qa.py check`, the critic's rounds (movement
5), `film.py render` and `deliver.py`. The letters are the order of `out/boards.png`: a, b, c.

## Rules that win

- Measured, never guessed: every share, color, time and count in brand.json and the written guide comes from what
  `research.py` measured from their posts, photographs and likes. Never invent a number or a caption; the voice
  lines are their own captions.
- Every word on screen is a word they gave: their opening line, their handle, their caption lines, their pillar
  names, their question, their sign-off. The film never shows their posting or engagement figures: posts, likes,
  comments, saves, followers and shares never reach the screen.
- What the person says about their own brand (their bio, the request, a look they name) wins over inference.
- Research comes first: nothing is drafted before `taste.md` and `brand.json` exist, and every word on screen and in
  the plan is in their voice (their case, their length, no exclamation marks if they use none).
- What to stop doing is said kindly: what those posts do, how they landed, never a judgment of the person.
- Look at what you make with the Read tool before any score: `out/boards.png` and each look's sheet, the cut's
  strips, and the story card, the image to post and the stills once they render.
- Every run makes the reel, the square and wide films, the story card and the image to post, the brand file, the plan,
  the caption and the review page. The stills render only when their words ask for them (`film.py render --also
  stories`; the words are in `S/pipeline/6-deliver.md`, "Render").
- The boards are written by the scripts. Change `taste.json` (or `cast.json` with a photo folder) and run the step
  again; never hand-edit a board, `film*.json`, `brand.json` or anything in `out/`.
- Each look is a style card (`S/styles/<id>.json`; `S/styles/catalog.md` says what each looks like). The standard
  every film is held to is `S/motion/system/standards.md`.
- A thin feed makes a shorter film, never a padded one; the scripts decide its length, so draft and check as usual.
- A film renders in chunks kept in the run (`render/chunks/`). When a render stops part way (the machine
  restarted, the session died), run the same command again: the finished chunks are kept and only the missing ones
  render. Never start over and never delete `render/chunks/`. Run `film.py cut` and `film.py render` each in the
  foreground in one tool call with a 40-minute timeout on that call, never in the background, and read its progress
  in `render/cut.log` or `render/film.log`: once the first chunks land, their time times the chunks still to go is
  the estimate to tell the person.
- Done means `deliver.py` printed `GATE GREEN`. Your reply then names the reel first: its full path from the project's
  root, exactly as deliver.py printed it on its last line, in a sentence ("Your reel is at
  build/20261026T014049Z/out/film.mp4"), never a bare `film.mp4`. Then, in two or three plain lines, anything else they
  asked for, their brand in its one-line statement, that `plan.md` in the same `out/` folder is the next 30 days, and
  that `review.html` there opens everything and shows the other two looks ("say 'make the second one'").
- A red gate is never a film to show: when deliver.py's last line says the gate failed, your reply says what failed
  and names no film, no path to one, and no review page.

## The kit's own tests

`python3 -I -m unittest discover -s tests` from this folder; the tests that read photographs skip when Pillow is
missing. `S/evals/blind.md` says what they cover and how a blind run is judged.
