# The critics

Three critics judge the storyboards (movement 3); two of them judge the finished cut (movement 6). Each one is a
voice you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photo move; is the type a system (two faces, a scale, consistent placement)
or a default; does each transition carry meaning; does the grade hold the film together; does anything collide,
crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does each card carry one idea and only one;
do the cards read in order as a set (the month, then what changed, the three that hit, their own words); does the
film carry the whole month in 15 s; does each beat earn its time; do the cuts land on the music; would you tap
through every card to the end.

**The person.** Speaks in the first person, from `build/taste.md` and their captions: "is this me?" Their photos,
their colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a
thing? The person breaks a tie in the storyboard vote.

## The seven criteria (1–5 each)

| key | criterion | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | studio-grade: eased, layered, a held grade, nothing collides | template feel, linear slides, text over busy photo, a crop that loses the subject |
| `them` | it is unmistakably them | their photos of the month carry it, their palette, their words, their own numbers against their year | generic stock mood, a voice that is not theirs, something from their avoid list |
| `pacing` | the pacing holds attention to the end | a rhythm with variation; each card settles early and then holds, readable; no beat outstays itself | uniform beats, a slow middle, text still typing when the card ends |
| `type` | type is a system, not a default | two faces, a scale, the same placement logic everywhere | mixed alignments, a stray size, headlines that wrap badly |
| `transitions` | every transition is intentional | each cut's preset means something (a page turn, a breath, a match) | the same crossfade everywhere, or flashy wipes with no reason |
| `music` | the music and the cuts agree | cuts on downbeats, the energy of the track matches the film's | cuts that ignore the beat, a track at odds with the tone |
| `series` | the cards read as one numbered series, one idea each, and they would post every one | one system across the cards (type, paper or field, the series mark counting up), each card a different idea, the last one inviting a reply | two cards that say the same thing, a card that breaks the system, a card they would skip |

## The storyboards (movement 3)

For each board look at `build/storyboards/N/sheet.png` (and any frame full size that you need), read its
`storyboard.md`, and score it as each critic in turn in `build/vote/scores.json`. A storyboard is a promise:
score the film it will become, from the frames you can see. Write one paragraph per board per critic, at least 25
words: what works, what fails, the one change you would make. The three boards are meant to be different; the
scores should show which difference suits this person.

## The cut (movement 6)

The motion designer and the person score the rendered film and every card. Look, actually look:

- `build/frames/sheet.png`, then every `build/frames/NN-<role>.png` (one per card) and `film-NN.png` full size
  with the Read tool;
- every static card in `out/cards/NN-<role>.png` (it is what a person sees when the story is paused);
- `build/qa/check.json` (the measured checks) and `build/render-report.json`.

Never score from memory of the storyboard; the cut is what ships. Fill in `build/critic/cut-N.json` and run
`vote.py verdict`. When a score is below 4, name the one change that fixes the worst thing in the paragraph, using
the levers below.

## The levers

- Words, photos, card order, beat lengths, transitions, clip prompts: the winner's
  `build/storyboards/N/storyboard.json`, then `storyboard.py check`, `snap`, `film.py render`.
- A photo: `grade.py photos FILE`, then `"graded/<name>.jpg"` in the beat.
- The grade and texture: `taste.json` (`palette`, `texture`), `grade.py recipe`, `grade.py photos`, `clips.py
  normalize`.
- The music: another track at `build/music/source.<ext>`, or `music.py make --mood calm|drive|film --bpm N`, then
  `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`.
