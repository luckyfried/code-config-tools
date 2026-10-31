# 5. Critic, gate, deliver

Goal: a cut at the bar (the mean of both critics' scores 4.5 or more and none under 4), or the one fix spent and the
best cut delivered with its scores in `build/brief.md`; a green `qa.py gate`; and `out/` complete and holding nothing
else: `film.mp4`, `carousel/` (10), `stories/` (3), `strip/` (the review page's frames), `looks/` (the other two
looks), `boards.png`, `caption.md`, `review.html`. The record of the run, `brief.md`, stays in `build/`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

Every round before deliver reads the half-size proof from `film.py render --proof`: while `out/proof.mp4` is the
newest render, `check` and `cut` read it and their first line says "reading the half-size proof". Every size they
report is in board units, the full-size reel's numbers, so a proof passes or fails exactly where the film would.

`check` measures the film and the cards: size, codec, fps, length, audio and loudness, black and frozen stretches
(over the whole film, the ending too: the closer keeps its slow push to the last frame), the render report, card sizes. Fix anything it fails before
the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md`, "The cut". As the motion designer, then as the person, open every `build/frames/*.png`,
a 12 frames a second strip of the newest reel (`out/proof.mp4` while it is there), the cards in `out/carousel/` and `out/stories/`, and fill in the round
file it names (`build/critic/cut-1.json`): a score 1 to 5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: the cut is at the bar; go on.
- `FIX ONCE`: it names every criterion at the lowest score. Read the critics' paragraphs and fix the one cause behind
  them at its cause (the words, a line or a scene, the music),
  run from `storyboard.py draft` through the vote and `film.py render --proof` again, then `vote.py cut` for round 2 (say in `fixed` what
  changed) and score again. After round 2 the fix is spent: deliver the cut as it stands, and
  `brief.md` carries its scores against the bar and says that it is under it. The person's page never shows a score.

## Render the full-size reel and read the type on it

Once the verdict on the proof is `SHIP` (or the fix is spent), render the reel at full size and score it once more:

```
python3 S/scripts/film.py render
python3 S/scripts/qa.py check
python3 S/scripts/vote.py cut
python3 S/scripts/vote.py verdict
```

`cut` moves the round to the full-size `out/film.mp4` and empties each critic's `type` score; the other scores stand.
As each critic, open the full-size reel's strip (`build/qa/film-strip2.png`) and the frames, read the type at the size
a phone shows it (`S/design/standards.md`, R3), and score `type` again. A `type` score that takes the round under the
bar here is a `FIX ONCE` like any other: fix it, render the proof again, and score round 2.

## Caption

Write `build/caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of their
own hashtags plus #yearinreview, about what they did, where and with whom, never how much they posted. Read their
captions in `build/taste.md` first. When you do not write one,
`deliver.py` drafts a short one from `taste.json`. Their captions give the voice, never the facts of a picture: a
post's caption often says what they felt, not what the photograph shows, so anything the caption says a photograph
shows comes from that month's `scene` in `build/picks.json`, the same words the brief's table of the year uses.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/review.html` (the person's page: it opens on the film with the hook's story card as
its poster and the strip of its frames beside it, then the caption, the cards, the other two looks under "Prefer
another look? Say 'make the second one'", and how the film was made in plain words; no score anywhere) and
`build/brief.md` (every door, every assumption, the three looks, the panel's scores and the pick, every clip and every
stand-in, the music's origin, the render, and the critics' scores of the cut against the bar), then runs `qa.py
gate`. `out/` holds only what is posted, that page with its strip and the looks, and `out/boards.png`; the gate
refuses an `out/` that holds anything else, and the storyboards and the brief stay in `build/`. On a red gate it names each failing check: fix the cause, then run `deliver.py` again.
`deliver.py` delivers only the full-size reel: when the newest render is the half-size proof it refuses with `not
delivered: the newest render is the half-size proof` and names the full-size render, `qa.py check` and `vote.py cut`
to run before it.

## Tell the person

The reply opens with the reel's full path from the workspace root, copied from the last line `deliver.py` printed,
in a sentence: "Your reel is at out/film.mp4." Never the bare name `film.mp4`. Then two or three plain lines: where
the cards are (`out/review.html` opens everything and shows the other two looks) and the idea of the film in one
sentence. When they ask for another look, run it as `SKILL.md`, "Which look", says.

When the gate has not passed, `deliver.py`'s last line is `the gate failed: ` and the failing checks' names, and it
prints no path. Fix what it names and run deliver.py again; when you stop before a green gate, the reply says
what failed in plain words and names no film and no path, so nothing points at a reel that is not ready.
