# 6. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and
`out/` complete: `film.mp4`, `story-1.png`, `story-2.png`, `story-3.png`, `countdown.png`, `feed.png`,
`captions.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film and the stills (size, codec, fps, a length of 15–30 s, audio and loudness, black and
frozen stretches, safe areas; the three stories at 1080×1920 and each different from the one before, the countdown
card at 1080×1920, the feed post at 1080×1350). Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`build/frames/NN-*.png`, the three stories, `out/countdown.png` and `out/feed.png`, and fill in the round file it
names (`build/critic/cut-1.json`): a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing in the storyboard (or the music, or a clip), run
  `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames`, then `vote.py cut` for round 2 (say
  in `fixed` what changed) and score again. After round 2 the fix is spent: ship, and brief.md names what is still
  below 4.

## Captions

Write `build/captions.md` in their voice, with six sections headed exactly `## film`, `## story 1`, `## story 2`,
`## story 3`, `## countdown` and `## feed post`. Every section names the product. The film and the feed post carry
one to ten hashtags, theirs first; the stories carry none or one. Use their case, their length, their kind of emoji
(or none), and open the film's caption the way their best hooks open. When they write in lowercase, every
section is lowercase except the product's name. Read their captions in `build/taste.md`
first. When you do not write one, deliver.py drafts all six from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/captions.md`, `out/brief.md` (the launch as given, the hooks ranked by response, what their
best-answered posts share, where the palettes meet, every door, every assumption, the vote, every clip and every
substitution, the music's origin, the engine, the critics' scores) and `out/review.html` (the film, the three
stories, the countdown card, the feed post, the captions, the three style sheets and the vote, with the
runners-up), then runs `qa.py gate`. On a red gate it names each failing check: fix the cause, then run deliver.py
again.

## Tell the person

Three or four plain lines: where everything is (`out/review.html` opens it all), the idea of the film in one
sentence, and that they can say "do the second one" for the runner-up.
