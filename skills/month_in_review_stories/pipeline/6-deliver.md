# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `cards/NN-<role>.mp4` and `cards/NN-<role>.png` for every card, `caption.md`,
`template.json`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film and every card: size, codec, fps, a length of 15 ±0.5 s, three to five cards each with a
1080×1920 PNG, audio and loudness, black and frozen stretches, safe areas. Fix anything it fails before the critics
watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open
`build/frames/sheet.png` and every `build/frames/NN-*.png` and `film-NN.png`, and fill in the round file it names
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
their own hashtags plus #monthinreview. Name the month and how many stories, and ask which one was their
followers' favorite the way they would. Read their captions in `build/taste.md` first. When you do not write one,
deliver.py drafts a short one from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`; `out/brief.md` (the month against their year and the three that hit first, then the
cards, every door, every assumption, the vote, every clip and every substitution, the music's origin, the engine,
the critics' scores); `out/template.json` (the series as a template: structure, card roles and titles, type,
palette, texture, motion, the series mark, which next month's `storyboard.py draft` reads so the series matches);
and `out/review.html` (the film, every animated card beside its static card, the caption, the three style sheets
and the vote, with the runners-up). Then it runs `qa.py gate`. On a red gate it names each failing check: fix the
cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the stories are (`out/review.html` opens everything), the idea of the series in
one sentence, post the cards in their numbered order, and that they can say "do the second one" for the
runner-up.
