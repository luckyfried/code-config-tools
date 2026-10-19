# The critics

Three critics judge the storyboards (movement 3); two of them judge the finished cut (movement 6). Each one is a
voice you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photo move; is the type a system (two faces, a scale, consistent placement)
or a default; does each transition carry meaning; does the grade hold the film together; does anything collide,
crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does the trip unfold (arrival, the days, the way
home) or just list places; is there a turn, a peak and a release; does each beat earn its time; do the cuts land on the music; does the ending make you
feel something and want to share it.

**The person.** Speaks in the first person, from `build/taste.md` and their captions: "is this me?" Their photos,
their colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a
thing? The person breaks a tie in the storyboard vote.

## The seven criteria (1–5 each)

| key | criterion | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | studio-grade: eased, layered, a held grade, nothing collides | template feel, linear slides, text over busy photo, a crop that loses the subject |
| `them` | it is unmistakably them | their trip: their places in their order, their people, their own clips and captions, the colors they travel in | generic stock mood, a voice that is not theirs, something from their avoid list |
| `pacing` | the pacing holds attention to the end | a rhythm with variation; quiet beats earn the loud ones; no beat outstays itself | uniform beats, a slow middle, a 5-second card with one word |
| `type` | type is a system, not a default | two faces, a scale, the same placement logic everywhere | mixed alignments, a stray size, headlines that wrap badly |
| `transitions` | every transition is intentional | each cut's preset means something (a page turn, a breath, a match) | the same crossfade everywhere, or flashy wipes with no reason |
| `music` | the music and the cuts agree | cuts on downbeats, the energy of the track matches the film's | cuts that ignore the beat, a track at odds with the tone |
| `ending` | the ending makes them want to post it | the whole route lands as the last image with the people who were there, one they would screenshot; the story cards make a set | an ending that just stops, a route that never resolves, a generic sign-off |

## The storyboards (movement 3)

For each board look at `build/storyboards/N/sheet.png` (and any frame full size that you need), read its
`storyboard.md`, and score it as each critic in turn in `build/vote/scores.json`. A storyboard is a promise:
score the film it will become, from the frames you can see. Write one paragraph per board per critic, at least 25
words: what works, what fails, the one change you would make. The three boards are meant to be different; the
scores should show which difference suits this person.

## The cut (movement 6)

The motion designer and the person score the rendered film. Look, actually look:

- every `build/frames/NN-*.png` full size with the Read tool, one per beat;
- a few frames of `out/film-16x9.mp4` (the same beats laid out wide: the words clear of the map, their clips whole
  over their blurred fill) and the five `out/story-N.png` cards (a set that reads in order);
- the route on the map: every place labeled once, no two labels on top of each other;
- `build/qa/check.json` (the measured checks) and `build/render-report.json`.

Never score from memory of the storyboard; the cut is what ships. Fill in `build/critic/cut-N.json` and run
`vote.py verdict`. When a score is below 4, name the one change that fixes the worst thing in the paragraph, using
the levers below.

## The levers

- Words, photos, order, beat lengths, transitions, clip prompts: the winner's
  `build/storyboards/N/storyboard.json`, then `storyboard.py check`, `snap`, `film.py render`.
- A photo: `grade.py photos FILE`, then `"graded/<name>.jpg"` in the beat.
- The grade and texture: `taste.json` (`palette`, `texture`), `grade.py recipe`, `grade.py photos`, `clips.py
  normalize`.
- The music: another track at `build/music/source.<ext>`, or `music.py make --mood calm|drive|film --bpm N`, then
  `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`.
