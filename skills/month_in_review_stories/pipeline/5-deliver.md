# 5. Critic, gate, deliver

Goal: a cut scored on the seven rules against the bar (a mean of 4.5, none under 4), at the bar or with its one fix
spent, a green `qa.py gate`, and the
run's `out/` complete: `film.mp4`, `cards/NN-story.mp4` and `cards/NN-story.png` for every card, `series.mp4` only when
they asked for it,
`caption.md`, `review.html`, and beside `out/` in the run, `brief.md` and `template.json`. Every path below is inside
the run's build folder, `build/<run stamp>/`, unless it says the workspace.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`film.py render` already ran it; run it again only after a render you made by hand. `check` measures every file in
`out/` again from the file itself and writes `qa/check.json` (the gate writes its own `qa/gate.json` and leaves it): size, codec and
profile, fps and length (the board's reel for the film, 15 s a card for the series when made and each card; unasked, `out/series.mp4` must
not be there), the cards'
stills, audio and loudness, black stretches, frozen stretches (in the film only before its stop, where the held
ending begins), the hook moving inside the first 30 frames, the render's findings, the length (with `seconds` asked,
the reel is that many seconds to the frame), and the look (every card still carries the board's ground and ink, its
palette's when the person gave a look). Beside the checks it writes
two figures that never pass or fail, for the critic to read with the strips: the cuts (planned and as the picture
shows them, and a minute) and the luma line's quiet seconds. Fix anything it fails before the critics watch: the
cause is in the board or the render, so rerun that movement. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md`, section "The cut". As the motion designer, then as the person, watch `out/film.mp4`
with sound, open `timeline/film-strip.png` (and `timeline/series-strip.png` when the series is made), `out/cover.png`
and every `out/cards/NN-*.png` with the Read tool, and fill in the round file it names (`critic/cut-1.json`): a score
1 to 5 per rule (or `"not read"`, with the reason) and a paragraph each, from this render's frames.
Running `vote.py cut` again before a new render names the same round; only a render that changes the files opens the
next one.

```
python3 S/scripts/vote.py verdict
```

- `AT THE BAR`: go on.
- `FIX ONCE`: it names the lowest rule under the bar that you have a lever for, and the lever (`S/critic/critic.md`,
  "The levers"). Change that one thing in `taste.json`, rerun movement 2 (draft, check, sheets, the vote) and
  movement 4 (`music.py make`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed`, `film.py render`),
  then `vote.py cut` for round 2: say in `fixed` what changed, and score the new frames.
- `SPENT`: the one fix is made, or no rule under the bar has a lever. Go on: the cut is delivered as the best one,
  and `brief.md` states every score against the bar. The review page never shows a score.

## Caption

Write the run's `caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
their own hashtags plus #monthinreview. Name the month and how many stories, and ask which one was their
followers' favorite the way they would. The caption goes with the reel. Read their captions in `taste.md` first. When you do not write one,
deliver.py drafts a short one from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`; `brief.md` in the run (the month's moments first, each with its day, place and their words, then the
cards in posting order, every door tried, every assumption, the vote, the music, the clips, the engine, the critics'
scores); `template.json` in the run (the month, the palette and its roles, the font, the numbering, the tone, the type files,
the devices on each card, the reel's beats and the axis rule: one card a moment, each in its post's cell of the wall of
the month's posts, which next month's `storyboard.py draft` reads as its look so the series matches); and
`out/review.html`, their page (the reel with `out/cover.png` as its poster, the caption, the series when made, every
animated card beside its still, the other two looks with "Prefer another look? Say 'make the second one'", and how it
was made in plain words; never a score, a rule or a critic). `out/` holds those and nothing else; the
storyboards, `brief.md` and `template.json` stay in the run. Then it runs the checks of `qa.py gate` in its own process; a score under the bar never
fails it. On a green gate it copies the run's `out/` to the workspace's `out/` and its
`template.json` to the workspace's `build/template.json`, and prints `GATE GREEN`. On a red gate it names each failing check: fix the cause, then run deliver.py again. The gate
must pass before the film is called ready. The last line deliver.py prints is the delivered reel's full path from the
workspace root, for example `build/20261026T005754Z/out/film.mp4`.
On a red gate the last line is `not delivered: the gate failed on <checks>` and names no film.

## Tell the person

Three or four plain lines. The first names the reel by that last line, copied exactly as deliver.py printed it: "Your
reel is at build/20261026T005754Z/out/film.mp4". Never the bare name `film.mp4` and never a path you typed. After it,
the review page (`out/review.html`, which opens the reel, the stories and the caption) may be named, then the idea of
the reel in one sentence, and that the cards post in their numbered order.

When the gate is still red, the reply says the film is not ready and which checks failed, in plain words, taken
from that last line, and names no film path and no review page.
