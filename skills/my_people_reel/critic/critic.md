# The critics

Three critics judge the three looks of the storyboard (movement 3); two of them judge the timed cut of the picked look
before the film renders (movement 5). Each one is a voice you take on in turn, with its own eye. They score the film
against the rules of `S/motion/system/standards.md` and the look's own style card (`S/styles/<id>.json`), each from the evidence the rule names and from nothing else. The
bar is a mean of 4.5 over the six scored rules with no rule under 4. Score what the evidence shows, and say why in
plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: does the tag decide every layout
and every move; do the photograph, its mount and the wall move as layers; is the type the card's two faces on one
scale, entering word by word and settled; is every move, cut, color and finish one the card gives; does anything collide, cut a face or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story and rhythm: does every beat show something the two
of them did; does the film build from the first person to the wall so the ending is earned; does the camera change its
move from beat to beat, gather before a big move and overshoot where it lands; does the peak hold longest and the
closer stand still; does each sound fall where a thing lands.

**The person.** Speaks in the first person, from `R/taste.md` and their captions: "is this me?" Their photos, their
colors, their people's own words, nothing on the avoid list. Would I post this today, without changing a thing? The
person breaks a tie in the storyboard vote.

## The six scored rules (1-5 each)

| key | rule | a 5 | a 3 or lower | read from |
|---|---|---|---|---|
| `R1` | one concept, every transition its own act | the tag is the idea: the hook tags everyone, the tag carries the camera from one photograph to the next, every person's tag returns on the wall where the camera rests; no move is a crossfade or a wipe | a move between beats the tag does not make, a beat that starts from nothing, a wall that does not pay the tags off | the 12 fps strip; the beats at rest |
| `R2` | depth, light, one grade | in every moving shot the photograph, its mount and the wall move at different rates; the card's finish over all (its grain, its light, its cadence), one grade on every photograph; a landscape photograph mounted the card's way with no dead blur around it; the closer's still stays still | a photograph sliding as one flat plane, half a frame of blur under a print, two grades in one film, a finish the card does not give | the beats at rest, full size; the strip |
| `R3` | type in motion, as a system | the card's two faces (its display face for the stamps, the tags and the title; its text face for every person's words) on one scale; words enter one by one on the card's curve with tracking that resolves, settled within a second; at rest every line is level, inside the safe area and clear of every edge and face; type takes its color from the field it sits on | a fade-in, a third face, a line tilted at rest, a line over a face, a paper strip under a line that already sits on paper | the beats at rest, full size; the strip |
| `R4` | motion and rhythm | one continuous camera; no two consecutive moves alike; a gather before each big move and an overshoot where it lands; a fast run followed by a hold; the peak holds longest; the closer holds still and silent after the stop | the same move beat after beat, a move that starts or stops dead, a closer that drifts | the strip: the frames between the rests |
| `R5` | sound to picture | each cue's onset in the waveform falls on the frame where its thing lands (the hook's landing, a stamp, the build into the wall and its impact, the last tag, the stop), and there is no sound over nothing; the effects 8 LU under the music | an onset a frame or more off its landing, a landing with no sound, a sound with nothing landing | the cue tiles `R/frames/cues/*.png` and `R/frames/cues.json`; `R/qa/check.json` (audio) |
| `R6` | generated shots are the spectacle | each request is a shot a cinematographer would write for its own photograph: who or what moves in it and how, the camera's move, the lens and the height, the light, the beat's length, seamless and loopable; the hook's world or a still brought to life; the light named from what the photograph's own light measures | a template with a handle pasted in, a shot that says nothing this photograph shows, a request with no lens or light, the same light or camera phrasing on every request, a prompt that asks for text or carries a person's words | `R/clips/requests.json` (`clips.py list`) |

`R7`, the deliverable, is measured, never scored: `qa.py gate` (its deliver check) reads the `out/` listing.

A rule whose evidence is missing scores 1, and its paragraph says which file was missing.

## The storyboard (movement 3)

For each of the three looks, look at its three sheets (`R/storyboards/<style>/sheet.png`, `sheet-square.png`,
`sheet-wide.png`) and any frame full size that you need, read its `storyboard.md` (every sound cue with its time, and
every clip the film asks for), and score it as each critic in turn in `R/vote/scores.json`. Each look is held to its
own card: a scrapbook is scored as a scrapbook, kinetic type as kinetic type. A storyboard is a promise: score the film it will become, each
rule from the part of the board that shows it (the frames of the sheets for R1 to R4, the cues for R5, the clips for
R6). Write one
paragraph per critic, at least 25 words: what works, what fails, the one change you would make.

## The cut (movement 5)

The motion designer and the person score the timed cut, before the film renders. Each rule is read from its own
evidence, the files `film.py cut` and `clips.py list` made for this cut:

- `R/frames/film-strip.jpg`, the cut at 12 fps, 24 frames a row: R1 (what the tag does between the beats) and R4 (the
  moves between the rests, the holds, the closer).
- every `R/frames/NN-*.png` full size, one per beat at rest: R2 and R3.
- the cue tiles, `R/frames/cues/NN-<kind>-<seconds>.png`, one per sound cue: the cut's frames every 0.2 s from 0.6 s
  before the cue to 0.8 s after it in one row, over the waveform of the film's sound across the same span, with the
  cue's time marked on the waveform. Each frame's left edge sits over its own time, so the onset is read against the
  frame where the thing lands. `R/frames/cues.json` lists each tile with its cue (beat, kind, what it lands on, its
  time), the times of its frames, and the music's onsets inside the span. This is how R5's cue placement is read.
- `R/qa/check.json`: the loudness of the music and of the effects under it (R5), and the figures (the cuts and their
  rate, the seconds whose picture barely changes, the hook frame).
- `R/clips/requests.json`: R6.

Never score from memory of the storyboard; the cut is what ships. Fill in `R/critic/cut-N.json` and run
`vote.py verdict`. For every rule below 4, name in the paragraph the one change that fixes the worst thing, using the
levers below.

## The verdict

A rule's score is the lower of the two critics'. The verdict states the mean and the least against the bar and never
blocks the render:

- at the bar (mean 4.5 or more, none under 4): render.
- under the bar in round 1: fix the rule furthest under it once, when one of the levers below reaches it, and cut
  again for round 2. When no lever reaches it, the budget is spent: render this cut.
- under the bar after the fix: render this cut as the best one.

`R/brief.md` states every score against the bar, whichever way it went; the review page the person reads carries none.

## The levers

- Order, beat lengths, which of a person's own lines: the picked look's `R/storyboards/<style>/storyboard.json`, then
  `storyboard.py check`, `snap`, `music.py master`, `film.py cut`.
- A photograph, its crop or its light: `R/cast.json` (another of their photographs, its `point`, `face`,
  `keep_light`), then `cast.py match`, `storyboard.py check`, `film.py cut`.
- The music: another track at `R/music/source.<ext>`, or `R/taste.json` `music` (its `styles` and `avoid` words) and `music.py find`, then `music.py analyze`,
  `storyboard.py snap`, `music.py master`, `film.py cut`.
