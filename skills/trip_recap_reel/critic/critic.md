# The critics

Three critics judge the storyboard (movement 3); two of them judge the finished cut (movement 6). Each one is a
voice you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft against the shared standard,
`motion/system/standards.md`, and the look's own card (`styles/<look>.json`): is every beat in the card's one finish
(its grade, grain, letterbox or flicker, at the card's values); does each photograph fill its frame, its subject clear
of the edges and the type; does the camera gather itself before it leaves and run a touch past its mark when it lands;
do two beats in a row make different moves, each one the card names and each chosen by what the beat holds; do the
letters set in the card's two faces, in one placement logic, never over a busy patch of photograph; does anything
collide, crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does the trip unfold (arrival, the days, the way
home) or just list places; does every stop show something they did there; is there a turn, a peak and a release; does
each beat earn its time, the shots of different lengths; do the cuts land on the music; does the closer land: the
cinematic title card closing behind its bars, the analog closing line under the flicker, the scrapbook's closed book.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos,
their colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a
thing?

## The seven criteria (1-5 each)

Each criterion scores the film against the rules of `motion/system/standards.md` it names: a 5 meets every one of them
in the frames, and each clause it misses costs a point. Name the missed clause in the paragraph.

| key | criterion | rules it reads | a 5 | a 3 or lower |
|---|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | R2, R3 (safe areas, nothing collides) | one finish over every beat, the card's; every photograph fills its frame; nothing collides | a beat in another light, a photograph boxed small in its frame, text over a busy photo, a crop that loses the subject |
| `them` | it is unmistakably them | R6, their trip | their places in their order, their people, their own clips and captions, the colors they travel in; every clip request a shot of what their photograph shows | generic stock mood, a voice that is not theirs, a request that pastes their caption, something from their avoid list |
| `pacing` | the pacing holds attention to the end | R4 (rhythm) | spans of different lengths; the peak stop holds longest; quiet beats earn the loud ones; no beat outstays itself | uniform beats, a slow middle, a 5-second card with one word |
| `type` | type is a system, not a default | R3 | the card's two faces, a scale, the same placement logic everywhere, the words moving between anchors as the photographs ask; settled within a second and still after | mixed alignments, a stray size, a line that blurs with the camera, every line in one corner |
| `moves` | every move carries the trip on | R1, R4 (one camera, anticipation and overshoot, consecutive moves differ) | each move one the card names, chosen by what the beat holds; the camera gathers before it leaves and settles past its mark; no two beats in a row make the same move | the same move every beat, a push that only zooms, bare ground at an edge |
| `music` | the music and the cuts agree | R5 | cuts on downbeats, a bed that belongs to the look, the music resolving as the closer lands | cuts that ignore the beat, a track at odds with the look, a fade where the ending should be |
| `ending` | the ending makes them want to post it | R1 (the payoff), R7 | the look's own closer with the trip's name and dates, held still, one frame they would screenshot; the cover is that frame; the story cards, when asked for, make a set | an ending that just stops, a closer with no name, a generic sign-off |

## The storyboard (movement 3)

Look at `storyboards/1/sheet.png` (its hook, densest moment and closer as styleframes) and any frame full size that
you need, read its `storyboard.md`, and score it as each critic in turn in `vote/scores.json`. A storyboard is a
promise: score the film it will become, from the frames you can see. Write one paragraph per critic, at least 25
words: what works, what fails, the one change you would make.

## The cut (movement 6)

The motion designer and the person score the rendered film, and only the film that is in `out/` now. After every
render, `qa.py check` measures it and `film.py frames` cuts its frames; `vote.py cut` refuses a film whose check or
frames are older than it, and `vote.py verdict` refuses a round whose frames are not this film's or whose paragraphs
repeat the round before word for word. Look, actually look:

- `frames/film-strip.png` (the film at one frame a second) and every `frames/strip-<beat>.png` (twelve frames across
  the span) full size with the Read tool: a span whose frames are all alike does not move;
- when the person asked for them, the wide and square strips (`film.py frames --film out/film-16x9.mp4 --out
  frames-16x9`, and the same for `film-square.mp4`): the same film framed again for each shape, the photograph
  filling the frame at every moment, nothing cut by the edge;
- when the person asked for them, the `out/story-N.png` cards (a set that reads in order, each a finished picture);
- the trip as the frames show it: every stop named once, its line their own caption, the trip's name and the dates
  on the closer;
- for the music score only, `qa/check.json` (the sound cues, the loudness and where the music stops).

Every score but the music's is read from the frames and strips alone, and every paragraph cites them by file and
time: what a frame shows moving, holding, reading or failing. A paragraph that cites the storyboard, a plan, the name of
a move, or what the kit's files intend is not a reading of the film; score again from the frames. Never score from
memory of an earlier round; the cut is what ships. Fill in `critic/cut-N.json` and run `vote.py verdict`. When a score is below 4, name the one change that fixes the worst thing in the paragraph,
using the levers below.

## The levers

- Where they stood in a photograph and what it looks at: `points.json` (`near`, `far`), then `storyboard.py draft`,
  `check`, `sheets`, the vote, `snap`, `film.py render`. The board is rebuilt from its inputs, so a lever is an input, never an
  edit to `storyboard.json` or `film.json`.
- The words on screen: the names in `taste.json` `names` and `label`, their captions as `trip.json` carries them.
- Which photograph shows a stop: the stop's photos in `picks.json`, then `draft` and the vote again.
- The grade and texture: `taste.json` (`palette`, `texture`), `grade.py recipe`, `grade.py photos`, `clips.py
  normalize`.
- The music: another track at `music/source.<ext>` with `music.py find --origin "..."`, or a corrected brief in
  `taste.json` `music` and `music.py find` again (a bed it made is made again whenever the brief's mood or tempo
  changed), then `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`.
