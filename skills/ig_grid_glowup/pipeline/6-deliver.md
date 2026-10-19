# 6. Critic, gate, deliver

Goal: a finished nine and film both critics score 4 or better on every criterion (or the one fix spent), a green
`qa.py gate`, and `out/` complete: `audit.md`, `grid-before.png`, `posts/01..09.png`, `grid-after.png`, `plan.md`,
`film.mp4`, `review.html`, `brief.md`.

## Measure, then look

```
python3 S/scripts/qa.py check
```

`check` measures the film (size, codec, fps, 15 s ±0.5 s, audio and loudness, black and frozen stretches, safe
areas), the nine posts (1080×1350 each, nine different pictures) and the two grid images. Fix anything it fails
before the critics look. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the designer, then as the person, open `out/grid-after.png`, every
`out/posts/NN.png`, `out/plan.md` and every `build/frames/NN-*.png`, and fill in the round file it names
(`build/critic/cut-1.json`): a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing (a post, a caption, the order, the music, a clip), run
  `plan.py check` if the plan changed, then `storyboard.py snap`, `music.py master`, `film.py render`,
  `film.py frames`, then `vote.py cut` for round 2 (say in `fixed` what changed) and score again. After round 2 the
  fix is spent: ship, and brief.md names what is still below 4.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/brief.md` (every door, every assumption, what each of the nine is made from, every generated still
and clip and how it arrived, the vote, the music's origin, the engine, the critics' scores) and `out/review.html`
(the audit, the grid after, the nine, the plan, the film, the three style sheets and the vote, with the
runners-up), then runs `qa.py gate`. On a red gate it names each failing check: fix the cause, then run deliver.py
again.

## Tell the person

Three or four plain lines: where everything is (`out/review.html` opens it all), the direction in one sentence,
when the first post goes up, and that they can say "do the second one" for the runner-up direction.
