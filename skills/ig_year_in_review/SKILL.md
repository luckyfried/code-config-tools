---
name: ig_year_in_review
description: "Makes a finished Instagram year in review: a vertical motion film of the person's year (under a minute for a full year, shorter for a sparse one) from their own posts, one month at a time in calendar order with their own words for what happened that month, in the look they pick from three (a home movie, kinetic type, a Swiss grid), plus a 10-card carousel, 3 story cards, a caption and a review page, saved to out/. Use for ANY request to recap someone's year on social media, however it is phrased: 'make my Instagram year in review', 'my year in review', 'Instagram wrapped', 'make me a wrapped', 'recap my year', 'my year on Instagram', '2026 recap reel', 'year recap video', 'my year in posts', 'what did I post this year', 'a recap of my Instagram', 'year in review reel/carousel/post', 'Facebook year in review'. The person wants the finished film and cards, not advice: never answer with a plan or a list of ideas; invoke this skill and make them."
---

# Instagram year in review: the pipeline

Someone wants their year as a film they can post. Run **every movement below, in order, every time**. Each one
names the file to read and the commands to run; read the file, the rules that matter live there.

**Ask one thing only: which look.** Everything else is a sensible assumption the scripts record in `build/brief.md`;
the person can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this kit's folder: the folder you read this SKILL.md from, wherever that is. Every command runs in a
fresh shell, so shell variables and `cd` do not carry over: **write the folder out in full in every command**, for
example `python3 /full/path/to/ig_year_in_review/scripts/qa.py gate`, and run every command from the workspace root.
Deliverables go in `out/`; everything else goes in `build/`.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks that this machine can make a film (Python with Pillow, ffmpeg, the browser the render draws in, and
the kit's built composition) and installs nothing. When it exits 1, tell the person the plain sentence it printed for
each missing piece and stop.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, read the lines on `picks-sheet.jpg`, then you write `taste.md` and fix `taste.json` | taste.md with its five headings |
| 2 | three looks | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `check`, `sheets`, look at `out/boards.png` | three boards, zero findings |
| 3 | the pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill the scores and the swap test, `vote.py tally`, then ask which look (or pick by taste), `vote.py pick N --why "..."` | `build/winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find`, `music.py analyze`, `storyboard.py snap`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed` and the four reads, `qa.py timed`, `music.py master`, `film.py render` | `out/film.mp4` and the cards |
| 5 | critic, gate, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Which look

`storyboard.py sheets` writes `out/boards.png`: the three looks side by side, numbered 1 to 3, each its hook, a month
and its ending, with its name and one plain sentence. Where you can ask the person (a conversation), show them
`out/boards.png` and ask which one to make, then run `vote.py pick <1|2|3> --why "<their words>"`. Where no one can
answer (`build/taste.json` `ask` is false), pick the one that fits `taste.md` best and say why in one line in `--why`.

The review page shows the other two looks under "Prefer another look? Say 'make the second one'". When the person
says that, run `vote.py pick 2 --why "they asked for it"` (the number they name, in `out/boards.png`'s order), then
the produce sequence again in the same workspace: `music.py find`, `music.py analyze`, `storyboard.py snap`,
`clips.py normalize`, `film.py preview`, `vote.py timed` and the reads, `qa.py timed`, `music.py master`,
`film.py render`, then movement 5. The pick clears the cut, music, preview, reads and scores of the look before it,
so nothing of it is reused.

## Rules that win

- The film is about what they did, where and with whom, never about how much they posted: no count, chart or total is
  on screen, and nothing on screen is invented.
- Research comes first: nothing is drafted before `build/taste.md` exists, and every word on screen is in their
  voice (`taste.json` `words`: their case, their length, no exclamation marks if they use none).
- Each look is drawn wholly from its style card (`S/styles/<id>.json`): its faces, the colors its palette rule makes
  from their year's palette, its moves and cuts (each beat's picked from what the beat shows), its finish and its
  ending. The story is the kit's: a hook where the year lands and every month flashes, the months in calendar order
  each with their own line, the story's peak held longest, and the year's chapters at the end.
- A sparse year makes a shorter film, never a refusal.
- The check refuses a board whose type leaves the reel's safe area at a rest, holds under 4.5:1, covers a month's
  subject, or is set under its smallest size.
- The handle on screen is the one the export's profile files give, or there is none; a stand-in handle (@you,
  @username, @your_handle and the like) on screen refuses every `storyboard.py` command.
- Change the moments, the words, the lines in `build/picks.json` or the taste, never a board by hand; do not
  hand-edit `build/film.json`, a board, `build/clips.json` or anything in `out/`.
- Look at what you make: the photographs' lines, `out/boards.png`, the timed cut's strip, the frames and the cards,
  with the Read tool, before any score or read.
- A clip that did not arrive stands in as the look's own move on the still photograph; `brief.md` says which.
- A render that stops partway resumes: run the same command again, and never delete `build/render/chunks/`. Run
  `film.py preview` and `film.py render` each in the foreground in one tool call with a 40-minute timeout on that
  call, and read `build/render/<name>.log` for where it stands.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, first where the
  reel is, its path from the workspace root copied from the last line `deliver.py` printed ("Your reel is at
  out/film.mp4", never the bare `film.mp4`), then that `out/review.html` opens everything and shows the other two
  looks, and the idea of the film in a sentence.
- A gate that has not passed ends `deliver.py` on `the gate failed: ` and the failing checks' names, with no path:
  fix them and deliver again, and if you stop there, say what failed and name no film and no path.

## Changing the kit

The kit's tests: `python3 -I -m unittest discover -s S/tests` from `S`. `S/evals/blind.md` is the cold run that proves
the whole pipeline on a fixture export.
