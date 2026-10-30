# 5. Critic, gate, deliver

Goal: a cut the critics have scored (at the bar, a mean of 4.5 and no rule under 4, or the one fix spent), a green
`qa.py gate`, and `RUN/out/` complete: `film.mp4`, `cover.png`, the three story cards in `stories/`, `then-now.png`,
`caption.md`, `review.html`, and `film-square.mp4` and `film-16x9.mp4` only when the person asked for them (nothing
else). The making-of, `RUN/brief.md`, sits beside `out/`, never in it. The words that turn each film on, through
`film.py render --also`: `square` when they say square, 1:1, or a film for the feed; `landscape` when they say wide,
landscape, horizontal, 16:9, or a film for YouTube or a screen.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures every film and card in `RUN/cut/` (`RUN/qa/check.json`, and `RUN/qa/strip.png` at 2 fps); `film.py
render` runs it on every new cut, and running it again measures the cut as it is. It fails a film in `cut/` nobody
asked for, and measures: size, H.264 High at
30 fps, length, audio and loudness, cuts per minute against the tone's range, the locked seconds on the rest line (the lowest second reported)
(the mean luma difference a second apart at 1/8 size, so grain does not count), the hook frame, black stretches,
safe lines, the builder's rules on the board as rendered in every format, the cover and the cards, the date order. Anything it
fails is a fault to fix before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, watch `cut/film.mp4`, open
`RUN/qa/strip.png`, `cut/then-now.png`, the story cards and `RUN/clips/requests.json`, and fill in the round file it names
(`RUN/critic/cut-<tone>-1.json`): a score 1-5 per criterion and a paragraph each. Running `vote.py cut` again on the
same film names the same round file; it opens the next round only once the film has changed, and it refuses a cut
`qa.py check` has not measured.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: the cut meets the bar; go on.
- `FIX ONCE`: round 1 is under the bar and a lever inside the run reaches a rule under it. Take the fix: it names
  the rule and the lever in `critic.md` (the music, the research the builder read); run the movements it touches
  again through `film.py render`, then `vote.py cut` for round 2 (say in `fixed` what changed) and score again. The
  gate's critic row stays red while the verdict is `FIX ONCE`.
- `DELIVER WITH SCORES`: the fix is spent, or no lever inside a run reaches the rules under the bar. Go on: the cut
  is delivered as the run's best, and brief.md states every score against the bar.

## Caption

Write `RUN/caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
their own hashtags. It carries the span as the closer does: in their own words where they say it (`said_span` in
`RUN/taste.json`, "fourteen months in"), and otherwise as their first and latest dates, never a span they did not
say (a line of theirs like "a year ago" is fine; "a year of pottery" or a counted "9 months" is not). Read their captions in `RUN/taste.md` first; the recent ones are the voice to write in. When you
do not write one, deliver.py drafts a short one from `taste.json` and `subject.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `caption.md` into `RUN/cut/`, `RUN/brief.md` (the timeline: the subject, the first post, the latest, the span and
every milestone, against the photographs the film shows; then every door, every assumption, the vote, the timing
round, the music's origin, where the film rendered, every round of the critics rule by rule against the bar, and the
posts whose line the film leaves off) beside the run's folders, and `review.html` into `RUN/cut/` (in the film's own
colors, its text at a contrast of 7 to 1 or more against its background: the film first with `cover.png` as its
poster, the caption to copy, the story cards and the then/now card, any asked-for films, the other two looks with how
to ask for one, and how the film was made in plain words; the page carries no score), then runs `qa.py gate`. A cut
under the bar is delivered with its scores stated in `brief.md`; the gate never refuses on a score. On a pass
it publishes `RUN/cut/` to `RUN/out/` in one rename, so `out/` holds the deliverables and nothing else. On a red gate
it names each failing check and leaves no `RUN/out/`: fix the cause, then run deliver.py again. A deliver stopped
partway leaves no `RUN/out/` either. deliver holds the run's lock while it works and runs the gate inside itself, so every
probe the gate makes holds the lock too; it refuses while a draft or a render is running in the run, and names it.

## Tell the person

The reply opens with the reel's full path from the workspace root, copied from the last line `deliver.py` printed,
in a sentence: "Your reel is at build/20261026-014049/out/film.mp4." Never the bare name `film.mp4`. Then two or
three plain lines: where the cards and the caption are (`out/review.html` opens everything), the span it covers, and
the idea of the film in one sentence; when they asked for a length the photographs could not make, one more line
with the length made and why, as `brief.md` states it.

When the gate has not passed, `deliver.py`'s last line is `not delivered: the gate failed on ` and the failing checks' names, and it
prints no path. Fix what it names and run deliver.py again; when you stop before a green gate, the reply says
what failed in plain words and names no film and no path, so nothing points at a reel that is not ready.
