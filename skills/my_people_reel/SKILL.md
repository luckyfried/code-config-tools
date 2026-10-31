---
name: my_people_reel
description: "Makes a finished film of the people someone spent the year with: a 9:16 motion film with a card per person (the photograph of the two of them, where and when, and a line of that person's own; the people found from tags, @mentions and comments, or all they name), a caption tagging them all, a story card, and a review page, saved to out/, with the film in 1:1 or 16:9 and a card per person when asked for. Use for ANY request for a film, reel, recap or post about the people in someone's year, however it is phrased: 'who I spent the year with', 'my people', 'my people 2026', 'friendship recap', 'the friends who made my year', 'my top friends as a video', 'best friends recap', 'who I hung out with most', 'a reel of my friends from this year', 'shout out my people', 'tag my friends in a year recap', 'my crew this year'. The person wants the finished film and the caption, not advice: never answer with a plan or a list of ideas; invoke this skill and make them. It asks one thing at most: which of three looks."
---

# My people: the pipeline

Someone wants a film of the people who made their year, with a caption that tags them all and a story card
to share it (and, when they ask, a story card for each of them). Run **every movement below, in order, every time**. Each one names the file to read and the commands to run;
read the file, the rules that matter live there.

**Ask one thing at most: which look.** The storyboard is drawn up in three looks, and `out/boards.png` shows them one
over another. Where you can talk with the person, show it and ask which one; where you cannot (`taste.json` `ask`
is `false`), pick the one that fits their taste and say why in one line. Everything else you decide: make the
sensible assumption, let the scripts record it in `R/brief.md`, and keep going. That holds for a long list of people
too: when the request names more people than one row of the closing wall holds, make the film of every one of them;
the board gives each a beat and the wall grows to hold them all.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders.

## Paths

`S` below means the folder this SKILL.md was read from, wherever that is. Every command runs in a fresh shell, so
shell variables do not survive between commands: **write the path out in full in every command**, for example
`python3 /path/to/my_people_reel/scripts/qa.py check`. Run every command from the workspace root.

`R` means the run folder. `gather.py` starts every run in a new `build/<run stamp>/` and writes its name to
`build/current`; every later script works there, so a rerun never overwrites an earlier build. Everything a run
writes is under `R`, and the deliverables, and nothing else, are in `R/out/`.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for what a film needs: python3 with Pillow, ffmpeg, a Chromium (Chromium or Google Chrome, or the
browser in `CHROME_PATH`), and the kit's built composition in `S/motion/dist/`. It installs nothing and takes about a
second. When it prints `"ok": true`, go on. Otherwise it says on its last lines what is missing, one sentence each;
tell the person those sentences and stop, since the film cannot render without them.

The film is drawn frame by frame in that Chromium, with no window, and encoded with ffmpeg. Working files (the
frames, the browser's profile) go under `~/.cache/code-config/my_people_reel/`, never into this folder.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `R/library.json` |
| 1 | research and cast | `S/pipeline/1-research.md` | `research.py [--people a,b,c] [--top N]`, write `R/taste.md`, fix `R/taste.json`, `cast.py draft`, correct `R/cast.json`, `cast.py match` | `R/public/matched/` |
| 2 | three looks | `S/pipeline/2-storyboards.md` | `storyboard.py draft [--style ID]`, edit, `storyboard.py check`, `storyboard.py sheets`, look | the three pass `check`; `R/out/boards.png` |
| 3 | the panel and the pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`, show `R/out/boards.png` and ask (or pick by taste), `vote.py pick LOOK [--why "..."]` | `R/winner.json` |
| 4 | the timed cut | `S/pipeline/4-produce.md` | `music.py find`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py cut`, `clips.py list`, `clips.py normalize` | `R/render/cut.mp4`, its 12 fps strip and cue tiles, `R/clips/requests.json` |
| 5 | critic, render, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score R1 to R6, `vote.py verdict` (fix once if told and a lever reaches it), `film.py render [--also ...]`, write `R/caption.md`, `deliver.py` | green gate |
| 6 | another look | this table | "make the second one" after a delivery: `vote.py pick second`, then movements 4 and 5 again in the same run | the new film's green gate |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- Their people are theirs by their own words first: when the request names people ("me, Dani and Theo", "my
  roommates @a and @b"), pass them to `research.py --people a,b,c` in the order given and never add or drop one,
  however many they name. Otherwise they are the people `R/people.json` found from every signal together (five
  unless they asked for a number: `--top N`, any number). Never swap someone in by taste. No count, rank, total or
  signal reaches the screen: each person's beat is the photograph of the two of them, the stamp of where and when it
  was taken (the photograph's own month and the place its caption names, else the one the person named most that
  month) and the other's own words.
- The three looks are three style cards (`S/styles/<id>.json`): scrapbook, analog home movie and kinetic type, or the
  style the person named and the two that differ most from it (`storyboard.py draft --style ID`). The story is the
  same in all three; each card decides the faces, colors, moves, finish, music and closer.
- Fewer people is still a film: with one person it runs about 9 s, and each person after adds 2 to 3.5 s, about 20 to
  25 s at five, and past five each one adds the same again. The storyboard decides this; nothing is padded with
  someone else and nobody is cut to keep it short.
- Each person's words are theirs: a comment they wrote, or, for someone who never comments, the person's own caption
  about them. You may pick a different one of their lines from `R/people.json`; never write one for them.
- Research comes first: nothing is drafted before `R/taste.md` exists, and every word on screen is in the person's
  voice (their case, their length, no exclamation marks if they use none).
- Every person is in the film; the caption tags every one of them. A person whose photographs never
  show a face (a back, a silhouette, hands) is cast by where they are in the frame; never claim a photograph shows
  someone it does not.
- Look at what you make: the sheets, `R/out/boards.png`, the strip, the beats at rest, the cue tiles and any story
  cards that were asked for, with the Read tool, before any score. Every score is read from this run's files, never
  from memory.
- The reel renders alone. `film.py render --also landscape square stories` adds the 16:9 film, the 1:1 film and a
  story card per person, each only when the person's words asked for it (`S/pipeline/5-deliver.md` says which words);
  the gate fails on any of them in `R/out/` that nobody asked for.
- Do not hand-edit `R/film.json`, `R/render/` or anything in `R/out/`; change the storyboard, the cast or the taste
  and run the step again.
- A film renders in chunks saved in the run. When a render is interrupted (the machine restarted, the session died),
  run the same command again: the finished chunks are kept and only the missing ones render. Never start over and
  never delete `R/render/chunks/`; a changed cut renders into chunks of its own. Run `film.py cut` and a long render each
  in the foreground in one tool call with a 40-minute timeout on that call, never in the background, and read its progress in `R/render/<cut|final>.log`; once the first chunks land, their time
  multiplied by the chunks still to go is the estimate to give the person.
- A cut under the bar is still delivered: the best cut ships, and its scores are written in `R/brief.md` only.
- Done means `deliver.py` printed its film path on a green gate; the gate must pass before the film is called ready.
  Then tell the person in three or four plain lines. The first names the reel by the full path from the workspace
  root that deliver.py printed on its last line, copied exactly, for example "Your reel is at
  build/20261020T151200Z/out/film.mp4"; never the bare name `film.mp4`. Then the review page (`R/out/review.html`:
  the film, its cover, the caption and the two other looks) may be named, who is in it and in what order, the idea of
  the film in a sentence, and that they can say "make the second one" for another look.
  A red gate's last line names the failing checks and no film: then say what failed and name no film.
