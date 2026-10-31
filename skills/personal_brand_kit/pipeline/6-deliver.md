# 6. Render, gate, deliver

Goal: a green `qa.py gate` and `out/` complete: `film.mp4` (the reel), `film-square.mp4`, `film-wide.mp4`,
`story.png`, `post.png`, `brand.json`, `plan.md`, `caption.md` and `review.html`, and `stills/` with `stills.json`
only when the person asked for them (nothing else). The run's notes, `brief.md`, stay in the run folder beside `out/`.

## Render

```
python3 S/scripts/film.py render
python3 S/scripts/film.py render --also stories   # only when the person asked for stills
```

`render` refuses until `qa/check.json` passes for this cut and the critic's latest verdict ships it or says the one
fix is spent. Then the reel is the cut itself with the mastered music laid under it, and every run also makes the
square film (`film-square.mp4`, 1080×1080) and the wide film (`film-wide.mp4`, 1920×1080), each from its own board
(the same story, the layout solved for the frame) with the same music, the story card (`story.png`, 1080×1920, the
reel's hook at rest: the film's cover) and the image to post (`post.png`, 1080×1080, the square's last moment at
rest). The stills render only when their words ask for them ("stills", "a carousel", "slides to post"): the square
film's beats at rest, one a beat in the film's order and at most ten, for an Instagram carousel. Every one of them is
the film's own frame, in its look and its type. A render takes away stills an earlier render left in `out/` that this
one was not asked for, and the gate fails on anything in `out/` that is not a deliverable.

The square and wide films render in chunks kept in the run, like the cut (movement 4): an interrupted `film.py render`
resumes when it is run again. The films, the cards and the stills reach `out/` only once every one of them is made.

Open the story card, the image to post, any stills, and a few frames of the square and wide films with the Read tool
before the gate.

## Caption

Write `caption.md` in the run folder in their voice, to post with the film or the stills: their case, their length,
their kind of emoji (or none), two or three of their own hashtags, a question the way they ask one. It speaks of the
moments the film shows, never a count: no posts, likes, followers or shares. Read their captions in `taste.md` first.
When you do not write one, deliver.py drafts a short one from `brand.json` in their register.

## Deliver

```
python3 S/scripts/deliver.py
```

It copies `brand.json` to `out/brand.json`, writes `out/caption.md`, and writes `out/review.html`, the film's cover:
it opens on the reel with the story card as its poster, then the square and wide films, the story card and the image
to post, the stills when they were made, the caption to copy, the other two looks (each its hook, a middle beat and
its closer, under "Prefer another look? Say 'make the second one'"), how the film was made in plain words, and their
brand: the palette as color, the voice, what they like elsewhere and what to stop. The page carries no score.

It writes the run's notes in `brief.md` beside `out/`: every door, every assumption, what the read found with its
numbers, what each beat of the film shows, the three looks and how the pick was made, the music's origin, how the
film was rendered, and the critics' scores of the cut against the bar, with what holds it under when the one fix was
spent. Then it runs `qa.py gate`.

The gate holds each film, at its own size, to the picture checks of `qa.py check` (size, length, black, frozen,
white, safe), and adds: the music on every film (AAC near 192 kbps, −14 LUFS within 1 LU, the effects at least 8 LU
under the bed), the story card at 1080×1920 and the image to post at 1080×1080, the asked-for stills (one to ten,
1080×1080, all different), nothing in `out/` that is not a deliverable, no placeholder in any word delivered, the
research, the three looks with their storyboards and sheets and `out/boards.png`, the pick, a critic verdict that
ships the cut the reel was made from or spends its fix, and the delivered files. On a red gate it names each failing
check: fix the cause, then run deliver.py again. On a green gate its last line is the reel's path from the project's
root, `build/<run>/out/film.mp4`.

## Tell the person

Your reply names the reel first: its full path from the project's root, exactly as deliver.py printed it on its last
line, in a sentence ("Your reel is at build/20261026T014049Z/out/film.mp4"). Never a bare `film.mp4`. Then, in two or
three plain lines: the square and wide films and the two images beside it, the stills when they asked for them,
their brand in the one-line statement, that `plan.md` in the same `out/` folder is the next 30 days, `brand.json` the
system other tools can read, and that `review.html` opens everything and shows the other two looks.

When they then ask for another look ("make the second one"), make it in the same run: SKILL.md, "Another look after
delivery".

When the gate failed, deliver.py's last line names the failing checks ("not ready: the gate failed on ...") and no
path: your reply says what failed, in plain words, and names no film, no path to one, and no review page.
