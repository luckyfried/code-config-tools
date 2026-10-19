# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `poster.png`, `caption.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film and the poster (size, codec, fps, a length of 30–60 s, audio and loudness, black and
frozen stretches, safe areas; the poster at 1080×1350). Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`build/frames/NN-*.png` and `out/poster.png`, and fill in the round file it names (`build/critic/cut-1.json`): a
score 1–5 per criterion and a paragraph each.

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
their own hashtags. It states how many places in digits beside the word ("11 places"), the count in
`build/places.json`, and no other count of places; name a few of the places the way they would. Read their
captions in `build/taste.md` first. A caption of yours that states no count gets one line with it on top. When you
do not write one, deliver.py drafts a short one from `taste.json` and `places.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/brief.md` (the places table first: every place in visit order with its dates,
visits, photos, distance from home and where it was found; then every door, every assumption, the vote, every clip
and every substitution, the music's origin, the engine, the critics' scores) and `out/review.html` (the film, the
poster, the caption, the three style sheets and the vote, with the runners-up), then runs `qa.py gate`. The gate
also checks that every place is in a beat of the film and in the brief's table, and that the caption's count equals
the number of places. On a red gate it names each failing check: fix the cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the film and the poster are (`out/review.html` opens everything), how many places
and the idea of the film in one sentence, and that they can say "do the second one" for the runner-up.
