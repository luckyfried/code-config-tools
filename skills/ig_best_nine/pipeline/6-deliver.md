# 5. Critic, gate, deliver

Goal: a cut both critics score 4 or better on every criterion (or the one fix spent), a green `qa.py gate`, and the
run's `out/` complete: `film.mp4`, `film-square.mp4`, `film-wide.mp4`, `best-nine.png`, `story.png`,
`caption.md`, `review.html`, `brief.md`.

## Measure, then watch

```
python3 S/scripts/qa.py check --run build/<stamp>
```

`check` measures the three films and the stills: size, codec, profile, fps and the length band; the audio and its
loudness; black stretches, and frozen stretches before the board's stop (the still a drive film holds from its stop
to the end is its ending); the render report's safe areas; the best-nine image at 1080x1080 and the story card at 1080x1920, each a closer at rest holding every post
whole. It prints the reel's cuts per minute and its luma line's seconds under 0.5 as figures for the critics, never a
pass or a fail, and writes them in `qa/check.json` `figures`. Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut --run build/<stamp>
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every
`frames/<format>-<rest>.png`, `out/best-nine.png`, `out/story.png` and the film's strip (`qa/film-strip2.png`), and
fill in the round file it names (`critic/cut-1.json`): a score 1 to 5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict --run build/<stamp>
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing at its cause (the words in `taste.json`, the music),
  run the steps again from `storyboard.py draft` or `music.py` through `film.py render`, then `vote.py cut` for
  round 2 (say in `fixed` what changed) and score again. After round 2 the fix is spent: ship, and brief.md names
  what is still below 4.

## Caption

Write the run's `caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
their own hashtags plus #bestnine. Ask which one is their followers' favorite the way they would. Read their
captions in `taste.md` first. When you do not write one, deliver.py drafts a short one from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py --run build/<stamp>
```

It writes `out/caption.md`, `out/brief.md` (the nine and why each worked, every door, every assumption, the vote and
its swap test, the music's origin, how the film was rendered, the critics' scores) and `out/review.html` (the three
films, the best-nine image, the story card, the caption, the sheet and the vote), then
runs `qa.py gate`. On a red gate it names each failing check: fix the cause, then run deliver.py again.

## Tell the person

Three or four plain lines: where the films, the best-nine image and the story card are (the run's `out/review.html`
opens everything) and the idea of the film in one sentence.
