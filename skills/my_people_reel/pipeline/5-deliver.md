# 5. Critic, render, deliver

Goal: a cut that passes `qa.py check`, scored by both critics on R1 to R6 against the bar (a mean of 4.5, no rule
under 4), then the film, a green `qa.py gate`, and `R/out/` complete: `film.mp4`, `cover.png`, `story.png`,
`caption.md`, `review.html`, and `film-square.mp4`, `film-wide.mp4` and `people/NN-<handle>.png` (one story card per person) only
when the person asked for them, and nothing else. How it was made, `R/brief.md`, stays in the run.

## The shapes the person asked for

The reel is what every request gets. The others render only when the person's own words ask for them, through
`film.py render --also`:

| their words | `--also` | adds |
|---|---|---|
| square, 1:1, for the feed or the grid, a post | `square` | `R/out/film-square.mp4` (1080x1080) |
| wide, landscape, 16:9, for YouTube, a TV or a screen | `landscape` | `R/out/film-wide.mp4` (1920x1080) |
| story cards, stories, a card for each of them, something to send each friend | `stories` | `R/out/people/NN-<handle>.png`, one 1080x1920 card per person |

"A video", "a reel" or "a recap" asks for the reel alone. The gate fails on a film or story card in `R/out/` that
the render did not make.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the cut and its board before anything else renders: the format (1080x1920 H.264 High at 30 fps,
8 to 30 s, and 4 s more for each person after the fifth), the audio and its loudness, black stretches, a frozen stretch before the board's stop (the still after
the stop is the ending), the hook inside the first 30 frames, the board in all three formats (`storyboard.py check`),
the render report, and every person on screen. It also writes two figures that are never a pass or a fail: the cuts
and their rate, and the seconds whose picture barely changes. Fix anything it fails in the storyboard or the cast
and cut again. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md`, section "The cut". As the motion designer, then as the person, score each rule from its
own evidence with the Read tool: the 12 fps strip (`R/frames/film-strip.jpg`), the beats at rest (`R/frames/NN-*.png`),
the cue tiles (`R/frames/cues/*.png`, with `R/frames/cues.json`: the frames around each sound cue over the waveform),
`R/qa/check.json` and `R/clips/requests.json`, and fill in the round file it names (`R/critic/cut-1.json`): a score
1-5 for each of R1 to R6 and a paragraph each. Run again on the same cut, `vote.py cut` names the same round; a new cut
opens the next one.

```
python3 S/scripts/vote.py verdict
```

The verdict states the mean and the least against the bar, and never stops the render:

- `AT THE BAR`: render.
- `FIX ONCE`: round 1 is under the bar, and it names the rule furthest under it. When one of the levers in
  `critic.md` reaches that rule, fix it in the storyboard, the cast or the music, run `storyboard.py check`, `snap`,
  `music.py master`, `film.py cut`, `clips.py list` and `qa.py check`, then `vote.py cut` for round 2 (say in `fixed`
  what changed) and score the new cut's files again. When no lever reaches it, the budget is spent: render this cut.
- `UNDER THE BAR after the fix`: render this cut as the best one. `R/brief.md` states every score, whichever way it
  went; the review page carries none.

## Render the film

```
python3 S/scripts/film.py render
```

Add `--also` with what the person's words asked for, and nothing else (for example `film.py render --also
stories`). `render` takes the checked cut as `R/out/film.mp4`; with `square` or `landscape` it lays the same storyboard
out again for 1:1 or 16:9 (each re-solved for its frame: the hook, the cards and the wall re-placed, never scaled to
fit) and renders it with the music; with `stories` it takes each person's story card from the settled frame of the
beat that names them: open every story card in `R/out/people/` with the Read tool. A film or story card in `R/out/`
from an earlier render that this one did not make is removed. It renders in chunks like the cut (movement 4): when it is interrupted, run
`film.py render` again and it picks up from the chunks already made; its progress is in `R/render/final.log`.
Every render also makes `R/out/cover.png`, the image the reel is posted with: the closer at rest at 1080x1920, and
`R/out/story.png`, the story card the reel is shared to a story with: the hook at rest at 1080x1920.
Nothing in `R/out/` changes until every film and story card it makes has rendered; then `R/out/review.html` and
`R/out/film.mp4` go, each deliverable moves in whole, and the reel moves in last, so a render stopped on the way
leaves an `R/out/` the gate and `deliver.py` refuse: run `film.py render` again. `deliver.py` writes the page again, saying it is not
ready until the gate passes.

## Caption

Write `R/caption.md` in their voice: their case, their length, their kind of emoji (or none), a line that says what
these people were to the year, then every person tagged (`@handle`, in the film's order), then two to four of their
own hashtags (none when they never use one). Read their captions in `R/taste.md` first. deliver.py adds anyone you left untagged; when you do not
write one, it drafts a short one that tags everyone.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `R/out/caption.md`, `R/out/review.html` (the person's page: the reel with `cover.png` as its poster, any
asked-for formats and story cards, the caption, the two looks that were not picked under "Prefer another look? Say
'make the second one'", and how it was made in a few plain sentences; no score), copies those two looks' sheets into
`R/out/looks/`, and, in the run folder beside `out/`, writes `R/brief.md` (every door, every assumption, the people,
each one's moment and why each is there, who came next, the three looks and the panel's scores, the pick and who made
it, the music's origin, how the film was rendered, the critics' scores against the bar), then runs `qa.py gate`. The gate fails
on anything in `R/out/` that is not a deliverable. On a red gate it names each failing
check: fix the cause, then run deliver.py again. The gate must pass before the film is called ready. The last line
deliver.py prints is the delivered reel's full path from the workspace root, for example
`build/20261020T151200Z/out/film.mp4`.
On a red gate the last line is `not delivered: the gate failed on <checks>` and names no film.

## Tell the person

Three or four plain lines. The first names the reel by that last line, copied exactly as deliver.py printed it:
"Your reel is at build/20261020T151200Z/out/film.mp4". Never the bare name `film.mp4` and never a path you typed.
After it, the review page (`R/out/review.html`) may be named (it opens the caption and anything else that was
asked for and the other two looks), then who is in it and in what order, the idea of the film in one sentence, and
that "make the second one" makes it again in another look.

## Another look

"Make the second one" (or "the scrapbook one", "C") after a delivery is `vote.py pick <look>`, then movement 4
(`music.py find`, `analyze`, `storyboard.py snap`, `music.py master`, `film.py cut`, `clips.py list` and `normalize`)
and this movement again, in the same run folder. The film delivered before is replaced by the new one.

When the gate is still red, the reply says the film is not ready and which checks failed, in plain words, taken
from that last line, and names no film path and no review page.
