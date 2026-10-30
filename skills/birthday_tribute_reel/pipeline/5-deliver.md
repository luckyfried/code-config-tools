# 5. Critic, gate, deliver

Goal: a cut both critics score at the bar (a mean of 4.5 with no score under 4), a green `qa.py gate`, and `out/`
holding the deliverables and nothing else: `film.mp4`, `post.png`, `story.png`, `caption.md`, `review.html`, and
`film-square.mp4`, `film-wide.mp4` and `stills/` only when the person asked for them. The run's record is
`B/brief.md`, never in `out/`.

## The shapes the person asked for

The reel is what every request gets. The others render only when the person's own words ask for them, through
`film.py render --also`:

| their words | `--also` | adds |
|---|---|---|
| square, 1:1, for the feed or the grid, a post | `square` | `out/film-square.mp4` (1080×1080) |
| wide, landscape, 16:9, for YouTube, a TV, a screen or the party | `landscape` | `out/film-wide.mp4` (1920×1080) |
| stills, photos to share, a story card, a picture of it | `stories` | `out/stills/`, the hook, the peak card and the closer of each rendered film |

"A video", "a reel" or "something for them" asks for the reel alone. `qa.py check` and the gate fail on a film or
still in `out/` that the render did not make.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the reel and any square film, wide film and stills that were asked for (size, codec and High
profile, 30 fps, a length of 20–60 s and within 1 s of the board's (the one the person asked for), the square and wide films within a second of the reel and with its sound, audio and loudness, black or white stretches,
frozen stretches before the board's stop, failed render jobs and fonts or photographs that failed to load, the stills of
every rest moment when asked for, and any shape in `out/` nobody asked for) and writes them to `B/qa/check.json` with two figures that never pass or fail: the cuts a minute
and each second's change. Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open every one of the 24
frames it cut into `B/critic/cut-N/`, `out/post.png`, `out/story.png` and any stills in `out/stills/`, and fill in
the round file it names (`B/critic/cut-1.json`): a score 1–5 per rule, a paragraph each naming the frames it read,
and the worst thing in the film in `worst`.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: the round is at the bar; go on.
- `FIX ONCE`: it quotes the worst thing the lowest-scoring critic found. Fix that thing, and not another one, with
  the levers in `S/critic/critic.md`, then run `storyboard.py snap`, `clips.py list`, `clips.py normalize`,
  `music.py master`, `film.py preview`, `vote.py timed` (the four reads again, from the new cut's frames),
  `qa.py timed`, `film.py render`, `film.py frames`, `qa.py check`, then `vote.py cut` for round 2 (say in `fixed`
  what changed and which frames show it) and score again from round 2's own frames.
- After round 2 the fix is spent: a film still below the bar delivers with the gate OPEN, and the review page and
  `B/brief.md` say what is below the bar.

## Caption

Write `B/caption.md` in the person's voice: their case, their length, their kind of emoji (or none), a line
for the named one, and their @handle, which the gate requires. Hashtags only if the person uses them (at most
ten). Read their captions in `B/taste.md` first. When you do not write one, deliver.py drafts a short one from
`taste.json` and `shared.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/review.html` (the film's cover: the reel opening on its story card, the caption to
copy, the posted image and the story card, any asked-for films and stills, and the critics' scores against the bar)
and `B/brief.md` (who the film is for and how they were found, the occasion, the film's length and where it came
from, what the two share, every door, every assumption, the vote, the music's origin, the clips, how the film was
rendered, the storyboard's sheet, the critics' scores against the bar), then
prints each assumption research made about who the film is for and which photos show them (`assumed: ...`), then
runs `qa.py gate`. The gate also checks that every photo on screen is one the two share and
that the caption names the named one. Its last line is `GATE GREEN` when every check passes, `GATE RED` when one
fails and `GATE OPEN (<checks>)` when none fails and one is open: the film below the bar once the fix is spent, or a
read that could not be made. On a red gate it names each failing check: fix the cause, then run deliver.py
again. A green or open run is marked delivered, keeps a copy of its deliverables in `B/out/`, and is never written again.
The gate must pass before the film is called ready. The last line deliver.py prints is the delivered reel's full path
from the workspace root, for example `build/20261020T151200Z/out/film.mp4`.
On a red gate the last line is `not delivered: the gate failed on <checks>` and names no film.

## Tell the person

Three or four plain lines. The first names the reel by that last line, copied exactly as deliver.py printed it:
"Your reel is at build/20261020T151200Z/out/film.mp4". Never the bare name `film.mp4` and never a path you typed.
After it, the review page (`out/review.html`) may be named, then the idea of the film in one sentence, and what to
say to change it. When deliver.py printed an `assumed:` line saying nothing in the posts tags or names them, say
which photos were used and why, in one line.

When the gate is open, the reply names the reel the same way and says, in one plain line, what is open (the
critics' scores against the bar, or the read that could not be made); it never calls the film ready or at the bar.

When the gate is still red, the reply says the film is not ready and which checks failed, in plain words, taken
from that last line, and names no film path and no review page.
