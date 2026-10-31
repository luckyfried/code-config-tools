# The critics

Three critics score the three storyboards (step 4); two of them score the finished film and posts (step 6). Each one
is a voice you take on in turn, with its own eye. Every score is against the seven rules below and the bar: a mean of
4.5 or more over the rules and no rule under 4, read on the lower of the two critics' scores for each rule. Score what
a paying client watching on a phone would notice, say why in plain words, and never round a score up.

## The panel

**The designer.** An art director who has built feeds and title sequences. Looks at craft: the idea and its motif,
the depth and light on every photograph, one grade across the film, the type as a designer sets it in the style's
faces, the nine posts as a set, the deliverable.

**The editor.** Cuts social films. Looks at rhythm and story: the hook in the first second, a different move on every
beat, anticipation before a move and a settle after it, the peak held longest, the closer landing with the ask, a cue
only where a beat lands, music that belongs to the style.

**The person.** Speaks in the first person, from `taste.md`, their captions and `audit.md` (when there is a feed): "is
this me?" Their photos, their colors, their voice, nothing on the avoid list; would I post the film and the nine next
week? The person breaks a tie in the vote.

## The seven rules (1 to 5 each)

| key | rule | a 4 or 5 | under 4 | read from |
|---|---|---|---|---|
| `concept` | R1 one concept carried from the hook to the closer, the closer paying it off | the hook states the glow-up in the first second; the frame is on every beat, carries each post into the grid, and opens as the profile's header in the closer; every change of shot is the frame's or the wall's own move | no idea in the first second, a beat the frame is not part of, a wipe or a crossfade, a frame that travels empty across the picture | the rests in `frames/` and the film's frames |
| `image` | R2 depth and light on every photograph, one grade, a composed closer | on a held post the subject's crop stands forward of its own photograph, which recedes behind it, and the wall sits behind both, each moving at its own rate; one grade from `taste.json` on every photograph, nothing cold in a warm feed; the closer composed with nothing cut by the frame | a flat card on one push, a photograph out of the grade, a closer that crops the grid or leaves dead space, a black or bare frame anywhere | the rests and the film's frames |
| `type` | R3 type set as a designer sets it, in the style's faces | the style's display face for the hook line and the ask, its text face for the handle and the bio, at a scale; letters enter and settle on the style's curves, inside the safe area | a line that fades or pops in, a default face, a line under the type floor, words in the unsafe area, an empty header | the hook's first second and the closer's frames |
| `motion` | R4 one continuous camera, anticipation and settle, no two beats alike in a row | anticipation before a big move and a settle where a thing lands; no two beats in a row make the same move; the middle held post, the peak, holds longest; the picture never sits frozen under the music | the same move twice in a row, a frozen hold before the stop, a peak that passes in under a second | `qa/film-strip12.jpg` and the film's frames |
| `sound` | R5 music that belongs to the style, cues on the landings, the stop on the ask | the bed is the picked style's own recipe (or the track they brought), a cue only where a beat lands, the effects 8 LU under the music, the music stops where the ask lands | a bed that fights the look, a cue off a landing, effects over the music, a stop off the ask | `qa/check.json`'s audio row (the loudness, the second each cue falls on, and the second the music stops) and `storyboard.md`'s music line; a session that cannot hear the mix says so in the paragraph |
| `posts` | R6 the nine posts designed in the style, each one a post the person would put up | each post is their own photograph in the picked look's crop, grade and type, the nine reading as one set and as a better version of their grid | a post that could be anyone's, two posts alike, a crop that loses the subject | `out/posts/` and `out/grid-after.png` |
| `deliverable` | R7 the deliverable is unmistakable | `out/` holds the films (one per shape), the posts, the story card, the caption file, the three boards and the review page, which opens on the film | a working file beside them, a page that opens on anything but the film | the `out/` listing and `out/review.html` |

## The boards (step 4)

Look at `out/boards.png` (the three looks side by side), then each `storyboards/<L>/sheet.png` (its hook, its densest
post and its closer) at full size, with its `storyboards/<L>/storyboard.md`, and `grid-before.png` beside them (when
there is a feed). Score each board as each critic in turn in `vote/scores.json` on the five rules a board shows
(concept, image, type, motion, posts), one paragraph per critic per board of at least 25 words: what works, what
fails, the one change you would make. As the designer, apply the swap test to each sheet: a frame passes when another
person's photographs, moments and words would change it, and fails when another person's grid would sit in it
unchanged.

## The cut (step 6)

The designer and the person score the film that will be delivered. Watch `out/film.mp4` at full size with the sound
on, as a client would, then look at the frames of THIS render, never the previous round's:

- every `frames/<format>-<rest>.png` (full size) and `qa/film-strip12.jpg`, the reel at 12 frames a second;
- `out/story.png`, `out/grid-after.png` and every `out/posts/NN.png`;
- the `out/` listing and `out/caption.txt`;
- `qa/check.json` (the measured checks of this render).

Fill in `critic/cut-N.json` on the seven rules and run `vote.py verdict`. A paragraph names, for every rule under 5,
what the frames show and the one change that would raise it.

## The verdict and its levers

`vote.py verdict` reads the round against the bar. SHIP: at the bar. FIX ONCE: the lowest rule with a lever below,
pulled once, then the steps the lever names, `vote.py cut` on the new render and its verdict. DELIVER: the fix is
spent, or no rule under the bar has a lever; the film is delivered as the best cut with every score stated in
`brief.md`. The verdict never stops a delivery.

| rule | the lever | then run |
|---|---|---|
| `concept`, `type` | the film's hook line and ask in `plan.json` (`film.hook`, `film.ask`) | `plan.py check`, then `storyboard.py draft`, `sheets` and `pick` (the same letter), `music.py` and everything after it |
| `image` | the grade: `taste.json` `palette` | `storyboard.py draft`, `sheets` and `pick` (the same letter) and everything after it |
| `posts` | each post's caption in `plan.json` | `plan.py check`, then `storyboard.py draft`, `sheets` and `pick` (the same letter) and everything after it |
| `sound` | the music: their track at `music/source.<ext>`, or `taste.json` `music` `styles` | `music.py find`, `analyze` (a track they brought), `master`, then `film.py render` and everything after it |
| `motion`, `deliverable` | none in the run: the kit makes them | the verdict counts the fix as spent |

`qa.py check` runs after every render.
