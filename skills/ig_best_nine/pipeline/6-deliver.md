# 5. Critic, gate, deliver

Goal: a cut at the bar (a mean of 4.5 or more, no criterion under 4), or the best cut after the one fix; a green
`qa.py gate`; and the run's `out/` complete: `film.mp4`, `best-nine.png`, `caption.md`, `review.html`, and
`film-square.mp4`, `film-wide.mp4` and `story.png` only when the person asked for them (nothing else). The run's
`brief.md` sits beside `out/`, never in it. The words that turn each extra on, through `film.py render --also`:
`square` when they say square, 1:1, or a film for the feed; `landscape` when they say wide, landscape, horizontal,
16:9, or a film for YouTube or a screen; `stories` when they say story, stories, or story card.

## Measure, then watch

Every round before deliver reads the half-size proof from `film.py render --proof`: while `out/proof.mp4` is the
newest render, `check` and `cut` read it and their first line says "reading the half-size proof". Every size they
report is in board units, the full-size film's numbers, so a proof passes or fails exactly where the film would.

```
python3 S/scripts/qa.py check --run build/<stamp>
```

`check` measures the reel (and the square and wide films when they were asked for) and the stills: size, codec,
profile, fps and the asked length within 1 s, and fails a film or story card in `out/` nobody asked for; the audio and
its loudness; black stretches, and frozen stretches of a second or more anywhere in the film, its ending included (every
beat moves to its cut, and the closer keeps its slow push to the last frame); the render report's safe areas; the best-nine image at 1080x1080 and an asked-for story card at
1080x1920, each holding every post whole. It prints the reel's cuts per minute and its luma line's seconds under 0.5
as figures for the critics, never a pass or a fail. Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut --run build/<stamp>
```

Read `S/critic/critic.md`, "The cut". Watch the film `cut` names (`out/proof.mp4` on a proof round), once, the way a
paying client would. Then, as
the motion designer and as the person, open every `frames/<format>-<rest>.png`, `out/best-nine.png`, `out/story.png`
if it was asked for and `qa/film-strip2.png`, and fill in the round file it names (`critic/cut-1.json`): a score 1 to
5 per criterion and a paragraph each. Never round a score up.

```
python3 S/scripts/vote.py verdict --run build/<stamp>
```

- `SHIP`: the cut is at the bar; go on.
- `FIX ONCE`: it names the worst thing and the levers. Fix that one thing at its cause: a beat's `layout`, `move` or
  `seconds` in `taste.json` `beats`, the words, or the music; run again from `storyboard.py draft` (then `vote.py
  pick` with the same look) or from `music.py`, through `film.py render --proof`; then `vote.py cut` for round 2 (say
  in `fixed` what changed) and score again.
- `UNDER THE BAR`: the fix is spent. Deliver this cut; `deliver.py` writes its scores into the run's `brief.md`.

## Render the full-size film and read the type on it

Once the verdict on the proof is `SHIP` (or the fix is spent), render the films at full size, with the same `--also`,
and score once more:

```
python3 S/scripts/film.py render --run build/<stamp>
python3 S/scripts/qa.py check --run build/<stamp>
python3 S/scripts/vote.py cut --run build/<stamp>
python3 S/scripts/vote.py verdict --run build/<stamp>
```

`cut` moves the round to the full-size reel and empties each critic's `type` score; the other scores stand. As each
critic, watch `out/film.mp4` at full size, open `qa/film-strip2.png` and the frames, read the type at the size a phone
shows it (`S/motion/system/standards.md`, R3), and score `type` again. A `type` score that takes the round under the
bar is a `FIX ONCE` like any other: fix it, render the proof again, and score round 2.

## Caption

Write the run's `caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
their own hashtags plus #bestnine. Ask which one is their followers' favorite the way they would. Read their captions
in `taste.md` first. When you do not write one, deliver.py drafts a short one from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py --run build/<stamp>
```

It writes `out/caption.md`, `out/review.html` and the run's `brief.md`, then runs `qa.py gate`.

- `out/review.html` is the film's cover: the reel, the best-nine image, the caption, any films and story card they
  asked for, the other two looks with "Prefer another look? Say 'make the second one'", and how it was made in plain
  words. It never shows a score.
- `brief.md` opens with the link to the review page, then the nine and why each worked, every door and assumption,
  the three looks and who picked which and why, the music's origin, how the film was rendered, and the critics'
  scores against the bar.

On a red gate it names each failing check: fix the cause, then run deliver.py again. deliver.py delivers only the
full-size film: when the newest render is the half-size proof it refuses with `not delivered: the newest render is the
half-size proof` and names the full-size render, `qa.py check` and `vote.py cut` to run before it.

## Another look

When they say "make the second one" (or the first, or name a look), make it in the same run:

```
python3 S/scripts/vote.py pick --run build/<stamp> --board <that look>
```

then movement 4 from `music.py find` and this movement again, through `deliver.py`. The review page names the other
two looks in the order "first" and "second".

## Tell the person

The reply opens with the reel's full path from the workspace root, copied from the last line `deliver.py` printed,
in a sentence: "Your reel is at build/20261026T014049Z/out/film.mp4." Never the bare name `film.mp4`. Then two or
three plain lines: that the run's `out/review.html` opens everything, the ranking `deliver.py` printed above the path
(what ranked the nine, or that they are the most recent posts and why, and that the reel counts down from the ninth
to the first while the grid reads first to ninth from its top left), the look and the idea of the film in one
sentence, and that they can say "make the second one" for another look.

When the gate has not passed, `deliver.py`'s last line is `not delivered: the gate failed on ` and the failing checks'
names, and it prints no path. Fix what it names and run deliver.py again; when you stop before a green gate, the reply
says what failed in plain words and names no film and no path.
