# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `then-now.png`, `caption.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film and the card (size, codec, fps, a length of 30–60 s, audio and loudness, black and
frozen stretches, safe areas; the then/now card at 1080×1350 pairing the earliest post with the latest; the film's
photo beats from the earliest post to the latest in date order, and every storyboard's too). Fix anything it fails
before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`build/frames/NN-*.png` and `out/then-now.png`, and fill in the round file it names
(`build/critic/cut-1.json`): a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing in the storyboard (or the music, or a clip), run
  `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames`, then `vote.py cut` for round 2 (say
  in `fixed` what changed) and score again. After round 2 the fix is spent: ship, and brief.md names what is still
  below 4.

## Caption

Write `build/caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
their own hashtags. It states the span exactly as `build/subject.json` `span.label` says it ("14 months"), and names
no other span (a line of theirs like "a year ago" is fine; "a year of pottery" when the span is 14 months is not).
Read their captions in `build/taste.md` first; the recent ones are the voice to write in. When you do not write
one, deliver.py drafts a short one from `taste.json` and `subject.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/brief.md` (the timeline it found: the subject, the first post, the latest, the
span and every milestone, against the film's photo beats; then every door, every assumption, the vote, every clip
and every substitution, the music's origin, the engine, the critics' scores) and `out/review.html` (the film, the
then/now card, the caption, the timeline, the three style sheets and the vote, with the runners-up), then runs
`qa.py gate`, which also checks that the caption's span is the span between the film's first and last photo beats. On a red gate it
names each failing check: fix the cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the film, the then/now card and the caption are (`out/review.html` opens
everything), the span it covers, the idea of the film in one sentence, and that they can say "do the second one"
for the runner-up.
