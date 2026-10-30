# The critics

Three critics judge the storyboard (movement 3), the editor reads the timed cut before it renders (movement 4),
and two of them judge the finished cut (movement 5). Each one is a voice you take on in turn, with its own eye. Every
score is against `motion/system/standards.md`, the seven rules of studio grade, and every film is held to the same bar: a mean
of 4.5 with no rule under 4. Score what a viewer would notice, from frames you have opened, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: does the photograph, its card
and the wall move at different rates, with a shadow under every card that flies and light wrapping its cut edges;
does one grade hold every photograph together; are there two faces and a scale, with names entering by letter and
tracking that resolves; does the camera anticipate a big move and overshoot where it lands, and never make the same
move twice in a row; does anything collide, crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does the hook state the idea in the first second;
is the wall carried across every cut and paid off in the closer; does the rhythm vary, with a fast run before a held
card and the year's peak holding longest; does a sound land where each beat lands and nowhere else; does the ending
make you want to send it.

**The person.** Speaks in the first person, from `B/taste.md` and their captions, as the one sending this to the named
one: "is this unmistakably us?" Our photos, the colors we share, my words to them and theirs to me, nothing on the
avoid list. Would I send this to them today, without changing a thing?

## The seven rules (1-5 each), the keys of every score

| key | rule | a 5 | a 3 or lower |
|---|---|---|---|
| `concept` | R1 one concept, motivated transitions | the hook states the wall of their year in the first second (the age rises out of the occasion photograph's line), every card's leave is its photograph trimming into its cell, and the closer's sheet cut from that wall pays it off | a beat that would be the same with any photograph (the swap test), a move between beats that is a preset, a hook photograph without the named one in it |
| `image` | R2 depth, light, one grade | in every held and moving shot the far part of the photograph, its subject, its card and the wall move at different rates; every photograph whole, in register with itself; a soft shadow under every card off the wall; light along every cut edge; grain over all; every photograph in one grade; the closer's still holds still | a photograph sitting flat while the camera moves, a photograph cut in two or out of register with itself, a card with hard edges and no shadow, a photograph in a different grade from its neighbors (a saturated one beside a gray one, a color cast, a veil over part of it) |
| `type` | R3 type in motion, as a system | two faces and a scale (the name, its words, the small lines); at most two tiers on a card; each name enters by letter with tracking that resolves, settled within a second; the name over its words on every card; every line at rest inside the safe area, nothing colliding | a third face, a stack of three tiers, a whole line sliding in or fading, words that swap sides from card to card, a widow, a capital in the lowercase, a line crossing the card's edge |
| `motion` | R4 motion and rhythm | one continuous camera; in the strip, no move between cards looks like the one before it (one runs along the wall, one pulls back to show more of it, one turns and tilts), each with a small counter-move in the frames before it and an overshoot where it lands; a fast run before a held card; the peak holds longest; the closer holds still and silent | the same move between every pair of cards, a whip that blurs the frame away, every card the same length, a landing that stops dead |
| `sound` | R5 sound to picture | a cue only where a beat lands; the effects 8 LU under the music; the bed in the brief's instruments; the music stops on the wish | a cue on a word that only rises, a bed that ignores the brief, music running past the wish |
| `clips` | R6 generated shots are the spectacle | each request in `clips/requests.json` a shot a cinematographer would write: its own subject and what moves in it, the camera's move, the lens feel and the camera's height, the light, the beat's length, a seamless loop; one for the hook's world, one of texture between chapters, one still brought to life | one sentence pasted onto several photographs, a request naming what is not in its photograph, a use missing |
| `deliverable` | R7 the deliverable is unmistakable | `out/` holds the films asked for, `post.png`, `story.png`, `caption.md` and `review.html`, which opens on the film with its cover | a process record, a sheet or a storyboard in `out/`, the post or the story card missing |

## The storyboard (movement 3)

Look at the board's three sheets, `B/storyboards/N/sheet.png`, `sheet-feed.png` and `sheet-wide.png` (and any frame
full size that you need), read its `storyboard.md`, and score it as each critic in turn in `B/vote/scores.json`. A
storyboard is a promise: score the film it will become, from the frames you can see. Write one paragraph per critic,
at least 25 words: what works, what fails, the one change you would make.

**The swap test.** For every beat with a photograph, imagine its photograph trading places with the neighboring
beat's. If the beat would come out the same design (the same crop logic, the same type in the same place, nothing
answering this picture's subject, lines or light), it is a template; a beat that another person's year would sit in
unchanged, a card whose words are not its own moment's, fails the same way. It passes when their photographs, their
moments and their words move the frame. List those beat ids in the board's `"swap"` (`[]` when every beat answers
its own photograph). A board with such a beat scores 3 or less on `concept`. The named beats are redesigned before
the film is cut: `storyboard.py snap` refuses while any of them is unchanged.

## The timed read (movement 4)

`vote.py timed` writes `B/critic/timed.json` for the cut `storyboard.py snap` timed, and cuts 24 frames of this cut's
preview into the folder it names (`frames`, each named like `9c1e-t07-27.50s.png`). As the editor, open every one of
those frames, and look at the preview's strip (`B/preview/film-strip2.png`). For
each read, a pass (true or false) and at least 25 words naming the beats and the frames you read them from (`9c1e-t07`):

- **carry**: one element is carried across every transition (the wall of their year, each moment's photograph
  going to its cell, from the hook to the closer).
- **sound**: a sound where each beat lands and nowhere else, under the music: the cues the board places
  (`measured.cue_seconds`) against where the effects stem's sounds start (`measured.effect_onsets`).
- **photograph**: the motion belongs to the photograph: put another photograph under the same move and it stops
  making sense.
- **held**: one held thing per beat, the moment's photograph and its line, and no beat holds still longer than its
  words need.

A read you cannot make from what is in front of you (no sound to hear, a frame that does not show the beat) is
`"pass": "not made"` with the reason in at least 8 words; it never passes. The file carries the preview's figures
(its cuts, cuts a minute, the seconds under 0.5 change, the frame of the hook's first event) beside the reads; they
inform the read and never pass or fail it. Every read is made again for every new cut, from that cut's frames: a read
written for another cut names none of this cut's frames and does not count. `qa.py timed` passes when every read that
is made passes; `film.py render` refuses while one fails; a read not made leaves the gate open and is told on the
review page. A failed read is fixed in the board, then `snap`, `music.py master`, `film.py preview` and a new read.

## The cut (movement 5)

The motion designer and the person score the rendered film. `vote.py cut` cuts 24 frames of `out/film.mp4` into
`B/critic/cut-N/` (each named like `r1-f07-16.25s.png`). Look, actually look:

- every one of those 24 frames full size with the Read tool, and the whole reel in `B/qa/film-strip2.png`, two frames
  a second;
- `out/post.png` and `out/story.png`, and when the person asked for stills, those in `out/stills/`;
- `B/clips/requests.json`, the `out/` listing, `B/qa/check.json` (the measured checks) and
  `B/render/film-report.json`.

Never score from memory of the storyboard; the cut is what ships. Fill in `B/critic/cut-N.json`: per critic the seven
scores, a paragraph of at least 25 words naming the frames it read (`r1-f07`), and in `worst` the worst thing in the
film in at least 8 words. Then run `vote.py verdict`. A round is at the bar when its scores average 4.5 or more and
none is under 4: SHIP. Below the bar, the verdict quotes the worst thing the lowest-scoring critic found; fix that
once with the levers below, re-render, and score round 2 from its own frames. A film still below the bar after the fix
delivers with its scores told on the review page and in the gate, never called green.

## The levers

- Photographs, order, beat lengths: the board's `B/storyboards/N/storyboard.json`, then `storyboard.py check`,
  `snap`, `film.py render`.
- The hook's photograph: taste.json `hook`, the post (`post:N`, or `post:N#K` for a carousel's K-th photograph) to open
  on, then `storyboard.py draft` again.
- A clip request: the beat's `shot` in the board (what the photograph shows and what moves in it), then `snap` and
  `clips.py list`.
- A photo: `grade.py photos FILE`, then its `"graded/<name>.jpg"` in the board's `photos`.
- The grade and texture: `taste.json` (`palette`, `texture`), `grade.py recipe`, `grade.py photos`.
- The music: another track at `B/music/source.<ext>` with `music.py find` and `music.py analyze`, or `taste.json`
  `music` and `music.py make`, then `storyboard.py snap`, `music.py master`, `film.py render`.
