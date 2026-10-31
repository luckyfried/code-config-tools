---
name: hype_reel
description: "Makes a finished hype reel about anything the person wants to celebrate: a product, a drop or an event, a friend, an idea, or a thing they follow (an account, a creator, a band, a place, a repo, a page). Delivers a 15 to 25 second vertical reel in the look they pick of three, a 1080x1350 feed post, a share caption, a cover and a review page, saved to out/; with a date or a launch, also three teaser stories and a countdown card carrying the date. Use for ANY request to hype, celebrate, tease or announce something, however it is phrased: 'make a hype reel for X', 'hype video for my friend', 'hype something up', 'what could you make for me', 'give me ideas for a reel', 'a reel about this account I love', 'announce my launch', 'hype video for my drop', 'event teaser', 'countdown stories', 'make a launch video for X on <date>', 'tease my new album/shop/app/book/menu', 'help me announce X'. The person wants the finished reel, not advice: invoke this skill and make it. When the request names no subject, it offers three to five ideas first; it asks at most two questions, which idea and which look."
---

# Hype reel: the pipeline

Someone wants a short, loud, true reel about one thing: what they are launching, a friend, an idea, or something they
follow. The kit makes the reel, a feed post, a share caption and a cover (the reel's strongest settled frame, also its
first frame); with a date or a launch, also three teaser stories and a countdown card. Run **every movement below, in
order, every time**. Each one names the file to read and the commands to run; read the file, the rules that matter
live there.

**Ask at most two questions.** When the request names no subject or only a vague one ("hype something up", "what
could you make for me"), the first is which idea: movement 0 drafts three to five, one line each, each naming a
subject and an angle, offered as clickable options (AskUserQuestion where the session has it, a numbered list elsewhere)
with "something else" always there. The other is which look, in movement 3. A request that names its subject skips the
first. Everything else comes from the request: make the sensible assumption for anything missing, let the scripts
record it in `out/brief.md`, and keep going. One picture of the subject makes a whole film; never stop to ask for
more. When `taste.json` `ask` is false, or there is no person to answer, pick the idea and the look yourself and say
why in one line each.

**Make what they asked for.** When they ask for only some pieces ("just the feed post"), run every movement as usual
(the stills are frames of the film) and name those pieces to `deliver.py` (`deliver.py feed`; the pieces are film,
feed, captions, cover, and for a launch stories and countdown): `out/` then holds only them and `brief.md`.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, the subject's folder or page, your music sources.

## Paths and runs

`S` below means the folder this SKILL.md was read from, wherever that is. Shell variables do not survive between
commands, and every command runs in a fresh shell, so **write the paths out in full in every command**, for example
`python3 /path/to/hype_reel/scripts/qa.py gate`. Run every command from the workspace root.

Each run lives in its own folder, `build/<run stamp>/`, which `gather.py` starts and `build/current` names; every
later script works inside it, so the paths in the movement files (`taste.md`, `storyboards/1/sheet.png`, `out/`)
are inside `build/current/`. The deliverables are that run's `out/`. A new run, or a recut, gets a new folder;
a run never overwrites another.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for what a film needs: python3 with Pillow, ffmpeg, a Chromium (Chromium or Google Chrome, or the
browser in `CHROME_PATH`), and the kit's built composition in `S/motion/dist/`. It installs nothing and takes about a
second. When it prints `"ok": true`, go on. Otherwise it says on its last lines what is missing, one sentence each;
tell the person those sentences and stop, since the film cannot render without them. Working files (the frames, the
browser's profile) go under `~/.cache/code-config/`, never into this folder.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | ideas, gather | `S/pipeline/0-gather.md` | with no subject named: `ideas.py`, then ask which idea; `gather.py --subject ... --kind ... --about ... [--date ...] --feed ... --door ...` | `library.json` with its `subject`, `settings` and `feed` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write `taste.md` and fix `taste.json` (its `plan`) | taste.md with its six headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `cast.py looks` and look, `storyboard.py draft`, `cast.py show`, `storyboard.py check`, `storyboard.py sheets`, look | three boards in three looks (`storyboards/1` to `3`), `out/boards.png`, check clean |
| 3 | pick | `S/pipeline/3-vote.md` | show `out/boards.png` and ask which look; `vote.py pick --board N` (with `--why "..."` when you picked) | `winner.json` |
| 4 | the cut | `S/pipeline/4-cut.md` | `music.py find` (it composes a bed with `music.py make` when they gave no track), `music.py analyze`, `storyboard.py snap`, `music.py master`, `clips.py list` and make the clips, `clips.py normalize`, `film.py cut` | `film.silent.mp4`, `qa/cut.json` passing |
| 5 | critics | `S/pipeline/5-critics.md`, `S/critic/critic.md` | `vote.py cut`, the reads and the scores, `vote.py verdict` (fix once if told) | `SHIP` |
| 6 | render, deliver | `S/pipeline/6-deliver.md` | `film.py render`, look, write `captions.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed; if it exits 2, there is no picture of the subject at all (`not
delivered: `). Tell the person the one sentence it printed and stop.

"Make the second one" (or the first, or the third) after a delivery is another look of the same run: run
`vote.py pick --board N` for that board in the same run, then movements 4 to 6 again.

## Rules that win

- Only true things. Every claim on screen and in a caption is the subject's own words, the person's, or a fact they
  gave or the subject's page states. No invented number, quote, testimonial or count of likes, followers or posts; a
  number on screen is one the subject or the person would say themselves. No secret, email address, phone number or
  other private detail ever appears on screen.
- An idea names only what the person can see themselves, and anything private read while drafting ideas (a message,
  a private account) appears on screen or in a caption only when the person picked that idea.
- The person's own words win: the subject's name, the date as they wrote it, the pictures or link they named, and
  anything they said about the subject or who it is for (into `taste.json` `said`). A length they asked for goes into
  `taste.json` `seconds` and is the film's length, moved into 15 to 25 seconds when it falls outside. Inference only
  fills what they did not say, and `brief.md` lists it as an assumption.
- Clear to a stranger: the hook (the first two seconds, planned first) says what this is about, the subject is shown
  for real, and every line can be read in its time on screen, about 0.3 s a word. Things arrive one at a time, every
  frozen frame is postable, and two busy layouts never crossfade through each other.
- The teaser stories and the countdown card are made only for a launch (a date in the request, or a launch with no day
  yet). The date on them and in the closer is the date they gave, set as they wrote it, never a guess.
- The films are made of the subject's own pictures and footage and the person's own photographs. The picked look sets
  the finish over the whole frame (`design/grade.md`); the subject's pictures keep their own color under it.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen and in the captions is
  in their voice. Every caption names the subject.
- Look at what you make: the feed sheet, the three storyboard sheets and `out/boards.png`, the strips of the cut, the
  cover, the feed post and, for a launch, the stories and the countdown card, with the Read tool, before any score.
- Do not hand-edit `film.json`, `clips.json` or anything in `out/`; change the storyboard or the cast and run the
  step again.
- The film renders in chunks saved in the run (`render/chunks/`). When a render is interrupted, run the same command
  again: the finished chunks are kept and only the missing ones render. Never start over and never delete
  `render/chunks/`.
- Run `film.py cut` and `film.py render` each in the foreground in one tool call with a 40-minute timeout on that call,
  never in the background, and read its progress in `render/render-report.log`. Once the first chunks land, their time
  times the chunks still to go is the estimate to tell the person.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, first where the
  reel is, its full path from the workspace root copied from the last line `deliver.py` printed ("Your reel is at
  build/20261026-014049/out/film.mp4", never the bare `film.mp4`), then that `build/current/out/review.html` opens it
  all, then the share caption, and the idea of the film in a sentence. When they asked for only some pieces, say where
  the first of those is and what the run assumed, and nothing about pieces they did not ask for. When `deliver.py`
  printed a line saying the length made and why, the reply carries that line word for word.
- A gate that has not passed ends `deliver.py` on `the gate failed: ` and the failing checks' names, with no path:
  fix them and deliver again, and if you stop there, say what failed and name no film and no path.
