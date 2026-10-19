# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `people/NN-<handle>.png` (one per person), `caption.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film and the cards (size, codec, fps, a length of 30–60 s, audio and loudness, black and
frozen stretches, safe areas; every person in at least one beat; one 1080×1920 card per person, no two the same).
Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`build/frames/NN-*.png` and every `out/people/*.png`, and fill in the round file it names
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

Write `build/caption.md` in their voice: their case, their length, their kind of emoji (or none), a line that says
what these people were to the year, then every person tagged (`@handle`, in the film's order), then two to four of
their own hashtags. Read their captions in `build/taste.md` first. deliver.py appends anyone you left untagged;
when you do not write one, it drafts a short one that tags everyone.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/brief.md` (every door, every assumption, the people and why each is there, who
came next and the order each signal alone would give, the vote, every clip and every substitution, the music's
origin, the engine, the critics' scores) and `out/review.html` (the film, the story cards, the caption, the three
style sheets and the vote, with the runners-up), then runs `qa.py gate`. On a red gate it names each failing check:
fix the cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the film, the story cards and the caption are (`out/review.html` opens
everything), who is in it and in what order, the idea of the film in one sentence, and that they can say "do the
second one" for the runner-up.
