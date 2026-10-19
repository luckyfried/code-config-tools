# The critics

Three critics judge the storyboards (movement 3); two of them judge the finished cut (movement 6). Each one is a
voice you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photo move; is the type a system (two faces, a scale, consistent placement)
or a default; does each transition carry meaning; does the grade hold the film together; does anything collide,
crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does the film move from where the two began
to now; is there a turn, a peak and a release; does each beat earn its time; do the cuts land on the music; does
the ending make you feel something and want to send it.

**The person.** Speaks in the first person, from `build/taste.md` and their captions, as the one sending this to
the named one: "is this unmistakably us?" Our photos, the colors we share, my words to them and theirs to me,
nothing on the avoid list. Would I send this to them today, without changing a thing? The person breaks a tie in
the storyboard vote.

## The seven criteria (1–5 each)

| key | criterion | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | studio-grade: eased, layered, a held grade, nothing collides | template feel, linear slides, text over busy photo, a crop that loses the subject |
| `them` | it is unmistakably the two of them | photos the two share carry it, uncropped where it counts; the shared palette; the person's words to them and theirs back | generic stock mood, a photo of someone else, a line neither of them would say, something from the avoid list |
| `pacing` | the pacing holds attention to the end | a rhythm with variation; quiet beats earn the loud ones; no beat outstays itself | uniform beats, a slow middle, a 5-second card with one word |
| `type` | type is a system, not a default | two faces, a scale, the same placement logic everywhere | mixed alignments, a stray size, headlines that wrap badly |
| `transitions` | every transition is intentional | each cut's preset means something (a page turn, a breath, a match) | the same crossfade everywhere, or flashy wipes with no reason |
| `music` | the music and the cuts agree | cuts on downbeats, the energy of the track matches the film's | cuts that ignore the beat, a track at odds with the tone |
| `ending` | the ending makes the person want to send it | the wish lands on the latest photo of the two of them, one the named one would screenshot; the card stands on its own | an ending that just stops, a generic sign-off, a card that needs the film to make sense |

## The storyboards (movement 3)

For each board look at `build/storyboards/N/sheet.png` (and any frame full size that you need), read its
`storyboard.md`, and score it as each critic in turn in `build/vote/scores.json`. A storyboard is a promise:
score the film it will become, from the frames you can see. Write one paragraph per board per critic, at least 25
words: what works, what fails, the one change you would make. The three boards are meant to be different; the
scores should show which difference suits these two.

## The cut (movement 6)

The motion designer and the person score the rendered film. Look, actually look:

- every `build/frames/NN-*.png` full size with the Read tool, one per beat;
- the square cut's frames (`film.py frames --film out/film-square.mp4 --out build/frames-square`): nothing cut
  off at 1080x1080, the two of them still in frame;
- `out/card.png` (1080x1350: the wish, the name, a photo of the two of them);
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
