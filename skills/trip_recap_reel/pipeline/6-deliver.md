# 6. Critic, gate, deliver

Goal: a cut that clears the bar (a mean of 4.5 or more, no criterion under 4; or the one fix spent), a green `qa.py gate`, and
the run's `out/` complete: `film.mp4`, `cover.png`, `caption.md`, `review.html`, and `film-16x9.mp4`,
`film-square.mp4` and `story-1.png` .. `story-5.png` only when the person asked for them (nothing else: no
storyboard, no vote, no brief; `brief.md` sits beside `out/`). The files named here are in the run's folder,
`build/<run>/`.

## What they asked for

The reel renders alone unless the person's words ask for more; `film.py render --also` names only what they asked for
(movement 4 renders it), and the gate fails on a shape in `out/` nobody asked for:

- `landscape` (`film-16x9.mp4`, 1920×1080): "16:9", "wide", "widescreen", "landscape", "for YouTube", "for a TV or a
  laptop screen".
- `square` (`film-square.mp4`, 1080×1080): "square", "1:1", "a square post", "for the grid".
- `stories` (`story-1.png` .. `story-5.png`): "story cards", "for my stories", "stills to share", "pictures to post
  with it".

"Reel", "video", "film" or "recap" alone asks for the reel alone.

## Measure, then watch

```
python3 S/scripts/qa.py check
```

`check` measures the film, any asked-for shapes and the board: size, codec and fps, a length within a frame of the
timed cut, audio and loudness, black stretches, frozen stretches before the board's stop (the end still after it is
the ending), white frames from a shader that failed, a render job, font or photograph that failed; an asked-for 16:9
or square film within 1 s of the film's length, and a 16:9 or square film in `out/` nobody asked for; asked-for story
cards five at 1080×1920, each a finished picture and no two the same, and a story card in `out/` nobody asked for;
and the board's check and monotony reads again. It writes `qa/check.json` with three figures for the critics: the
cuts as planned and as the picture shows them, the luma line and its quiet seconds, and the sound cues with the
last one before the stop. Fix anything it fails before the critics watch. Then:

```
python3 S/scripts/vote.py cut
```

`cut` refuses until `qa/check.json` and `frames/` (movement 4's `film.py frames`) both describe the film now in
`out/`: a render after either one means running it again. Read `S/critic/critic.md` section "The cut". As the motion designer, then as the person, open
`frames/film-strip.png`, every `frames/strip-<beat>.png`, and the wide and square strips and the story cards when
they were asked for, and fill in the round file it
names (`critic/cut-1.json`): a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: go on.
- `FIX ONCE`: it names the worst thing. Fix that one thing at its input (a point, a name, the music, a clip), run
  `storyboard.py check`, `storyboard.py snap`, movement 5, `music.py master`, `film.py render`, `film.py frames`,
  `qa.py check`, then `vote.py cut` for round 2 (say in `fixed` what changed). Watch the new frames and score again:
  the verdict refuses a round whose frames are the last film's or whose paragraphs repeat round 1. After round 2 the
  fix is spent: ship the best cut; brief.md carries its scores against the bar and names what is still below 4,
  and the review page carries none.

## Caption

Write `caption.md` in their voice: their case, their length, their kind of emoji (or none), two to four of
the hashtags they used on the trip's own posts, and none when they use none. Name the trip, the places and the people the way they would. Read
their captions in `taste.md` first. When you do not write one, deliver.py drafts a short one from
`taste.json`.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `out/caption.md`, `brief.md` beside `out/` (the trip first: its dates, each day and its places, every place in
route order, the people, travel against everyday; then every door, every assumption, the vote, every clip and every
stand-in, the music's origin, how the film was rendered, the critics' scores) and `out/review.html`, the film's
page (on the board's paper in its ink: the trip's title, the film with `cover.png` as its poster, the caption to
copy, the cover to post with, any asked-for shapes and story cards, the two other looks from `out/boards.png` with
"Prefer another look? Say 'make the second one'", and how it was made in plain words; it carries no score, and
nothing on it links outside `out/`), then runs `qa.py gate`, which adds the text,
research, board, vote, clips, critic and deliver checks to the measured ones. On a red gate it names each failing
check: fix the cause, then run deliver.py again. On a green gate its last line is the reel's path from the
project's root, `build/<run>/out/film.mp4`.

## Tell the person

Your reply names the reel first: its full path from the project's root, exactly as deliver.py printed it on its last
line, in a sentence ("Your reel is at build/20261026-014049/out/film.mp4"). Never a bare `film.mp4`. Then, in two or
three plain lines, any shapes they asked for beside it, the idea of the film in one sentence, and `review.html` in the
same `out/` folder, which opens everything.

When the gate failed, deliver.py's last line names the failing checks ("not ready: the gate failed on ...") and no
path: your reply says what failed, in plain words, and names no film, no path to one, and no review page.


When they then say "make the second one" (or the third, or name a look), pick that board (`vote.py pick --board N
--why "..."`) and run movement 4 from `music.py find` and this movement again; the new film gets its own page.
