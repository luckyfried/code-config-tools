# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `cards/01..10`, `brand.json`, `plan.md`, `caption.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film (size, codec, fps, a length of 20–30 s, audio and loudness, black and frozen stretches,
safe areas), the ten cards (in order, 1080×1350, ten different images), `brand.json` (the schema, pillar shares
summing to 1), `plan.md` (30 dated entries, each naming a pillar from `brand.json`, each with a caption) and the
guide's colors (every color a card names is in `brand.json`). Fix anything it fails before the critics watch.
Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`build/frames/NN-*.png` and all ten `out/cards/*.png`, and fill in the round file it names
(`build/critic/cut-1.json`): a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing at its source (the storyboard, `taste.json` and
  `brand.py system` for a card, the music, or a clip), run `storyboard.py snap`, `music.py master`,
  `film.py render`, `film.py frames`, then `vote.py cut` for round 2 (say in `fixed` what changed) and score
  again. After round 2 the fix is spent: ship, and brief.md names what is still below 4.

## Caption

Write `build/caption.md` in their voice to post with the film or the cards: their case, their length, their kind
of emoji (or none), two or three of their own hashtags, a question the way they ask one. Read their captions in
`build/taste.md` first. When you do not write one, deliver.py drafts a short one from `brand.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It copies `build/brand.json` to `out/brand.json`, writes `out/caption.md`, `out/brief.md` (every door, every
assumption, what the read found with its numbers, the vote, every clip and every substitution, the music's
origin, the engine, the critics' scores) and `out/review.html` (the film, the ten cards, the caption, the three
style sheets and the vote, with the runners-up), then runs `qa.py gate`. On a red gate it names each failing
check: fix the cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the guide and the film are (`out/review.html` opens everything), their brand in
the one-line statement, that `out/plan.md` is the next 30 days and `out/brand.json` the system other tools can
read, and that they can say "do the second one" for the runner-up film.
