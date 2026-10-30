# 5. Critic, gate, deliver

Goal: a cut both critics scored on every rule, a green `qa.py gate`, and the run's `out/` complete and holding nothing
else: the three films, `post.png`, `story.png`, `caption.md`, `boards.png` and `review.html`. `brief.md`, the run's
record, is in the run's folder beside `out/`. The critics' scores never stop the film: a cut under the bar is delivered
as the best cut the run made, with every score stated in `brief.md` and none on the review page.

## Measure, then watch

`film.py render` ended with `qa.py check`, which measures the three films and the two images and writes
`qa/check.json`; run `python3 S/scripts/qa.py check` again whenever you want it read once more:

| check | refuses |
|---|---|
| format | `out/film.mp4` not 1080×1920 H.264 High, `out/film-16x9.mp4` not 1920×1080 or `out/film-square.mp4` not 1080×1080 H.264; any of them missing, not yuv420p at 30 fps or outside the cut's band (20 to 40 s, or from the longest its stops make when that is under 20 s) |
| audio | with music, no AAC track near 192 kbps, loudness off −14 LUFS by more than 1 LU, a true peak over −1.5 dBTP |
| black | a black stretch of 0.4 s or more |
| frozen | a frozen stretch of 1.0 s or more that starts before the board's stop (the still after the stop is the ending) |
| safe | a failed render job, a font, a photograph or a shader that failed (`render/film-report.json`) |
| cards | `out/post.png` not 1080×1080 or `out/story.png` not 1080×1920, either missing or an empty frame |

`qa/check.json` also carries the figures the critics read with the strips, never a pass or a fail: the cuts as planned
and as the picture shows them, cuts per minute, the luma line and its quiet seconds. The reel's strips are in `qa/`
(`film-strip2.png` at 2 fps and `film-strip12-NN.jpg` at 12 fps). Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

`cut` takes the frames a round reads into `critic/cut-N/`: the first frame, sixteen at equal spacing, each beat as
the camera leaves it, and each shape's closer at rest at full size. Read `S/critic/critic.md` section
"The cut". As the motion designer, then as the person, view every one of those frames, the strips, `frames/`,
`out/post.png` and `out/story.png`, and fill in the round file it names (`critic/cut-1.json`): a score 1–5 per rule
and a paragraph each, every frame you viewed in `seen`, and a rule you cannot read here (R5's cue placement when
nobody can watch with sound) as `null` with its reason in `unread`. When a score is under 4, `lever` names the one
change from critic.md's levers that fixes the worst rule, or `none` when no lever reaches it.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on. It prints every rule's score; `brief.md` states them.
- `FIX ONCE`: it names the worst rule and its lever. Make the lever's change in its source, then run the steps after
  it (critic.md, "The levers") through `film.py render`, then `vote.py cut`, which opens round 2 on the new film and
  its own frames; say in `fixed`, in at least eight words, what changed, and score again from those frames.
  `vote.py cut` refuses to open round 2 on the film round 1 scored. Round 2 is the last: its verdict is `SHIP`
  whatever the scores, and `brief.md` names what is still under 4.

## Caption

Write `caption.md` in the run's folder, in their voice: their case (when `taste.json`'s register says lowercase, most of their captions are lowercase
throughout, so the whole caption is, place names too, and qa.py gate holds it to that), their length, their kind of emoji (or none), two
to four of their own hashtags (none when they write none). It states how many places in digits beside the word ("11 places"), the count in
`places.json`, and no other count of places; name a few of the places the way they would. Read their captions in
`taste.md` first. A caption of yours that states no count gets one line with it on top. When you do not write one,
deliver.py drafts a short one from `taste.json` and `places.json`. A caption must agree with the photographs: a place
it names is a place the film shows. When it does not, the place list is wrong, and the fix is in `places.json`
(`places.py --rename/--drop`) or the visit's `place` in `cast.json`, never in the caption alone.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `out/review.html` and the run's `brief.md`, then runs `qa.py gate`. `review.html` is the
film's cover: the reel with the story card as its poster, the caption with a button to copy it, the posted image and
the story card, the 16:9 and square films, the two looks not picked (cut from `out/boards.png`) under "Prefer another
look?" with the words to ask for one ("make the second one"), and how it was made in plain words. It carries no score.
`brief.md` is the record, in the run's folder: the places table first (every place in
visit order with its dates, visits, posts and where it was found), then the photographs each visit shows and where
each came from, every door, every assumption, the vote, the music's origin, how long the film runs and how it was
rendered, and the critics' scores of the cut against the bar. The gate runs timed and check and adds: a placeholder in any word, every place named on its
strip, the caption's count equal to the number of places, the research, the storyboard, the vote, a complete critic
round for the film in `out/` (its scores are stated, never a fail) and `out/` holding the deliverables and nothing
else. On a red gate it names each failing check: fix the cause, then run deliver.py again. On a green gate its last
line is the reel's path from the project's root, `build/<run>/out/film.mp4`.

## Tell the person

Your reply names the reel first: its full path from the project's root, exactly as deliver.py printed it on its last
line, in a sentence ("Your reel is at build/20261026-014049/out/film.mp4"). Never a bare `film.mp4`. Then, in two or
three plain lines: `review.html` in the same `out/` folder opens everything, how many places, how long the film runs (when
they asked for a length the places could not make, the length made and why, as `brief.md` states it), and the idea of
the film in one sentence.

When the gate failed, deliver.py's last line names the failing checks ("not ready: the gate failed on ...") and no
path: your reply says what failed, in plain words, and names no film, no path to one, and no review page.

