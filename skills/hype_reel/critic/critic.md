# The critics

Three critics judge the storyboards (movement 3); two of them judge the timed cut (movement 5), before the film
renders with its music and its stills. Each one is a
voice you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft, against the look's own style
card: does every frame carry the card's finish (its grade, grain, bars or page) and one grade holding the film
together; does each move suit what its beat holds and land on the music; is the type the card's two faces at one
scale with one placement logic, every word readable; does each cut and each move carry meaning; does anything collide,
crop badly or sit outside the safe area.

**The editor.** Cuts hype reels, trailers and social promos. Looks at story: does the opening stop the thumb in the
first second and tell a stranger what this is about; does the tease hold back enough that the reveal pays; is there a
build, a reveal and a release; does each beat earn its time and read in it, about 0.3 s a word; does everything
arrive one thing at a time; is every claim true and in the subject's or the person's own words; do the cuts land on
the music; does the closer's punchline, or a launch's date, land so a viewer remembers it.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me, hyping the thing I
love?" The subject shown for real from its own pictures, the true things about it in its own words or theirs, their
colors meeting the subject's, nothing on the avoid list, nothing private on screen. Would I post this today, with the
share caption, without changing a thing? The person breaks a tie in the storyboard vote.

## The seven criteria (1–5 each)

Each criterion scores the film against its own style card and the rules of `S/motion/system/standards.md` it names:
a 5 meets every one of them in the frames, and each rule it misses costs a point. Name the missed rule in the
paragraph.

| key | criterion | rules it reads | a 5 | a 3 or lower |
|---|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | R2 (the card's finish), R3 safe areas | studio grade: every frame in the card's finish, one grade over all, the subject lit and whole, nothing collides | template feel, a picture cropped past its subject, text over a busy photograph, a frame that leaves the card |
| `them` | it is unmistakably them and unmistakably the subject | made of this subject and this person, R6 | the subject from its own pictures and footage and on screen for most of the film, true lines in its own words or theirs, the subject's colors meeting theirs | a layout with slots, a photograph that is not what the line says, a voice that is not theirs, something from their avoid list |
| `pacing` | the pacing holds attention to the end | R4 rhythm, something arrives at once | a rhythm with variation; quiet beats earn the loud ones; the reveal holds longest; no beat outstays itself | uniform beats, a slow middle, a 5-second card with one word |
| `type` | type is a system, not a default | R3 (the card's faces, every word reads) | the card's two faces at one scale with one placement logic, every line readable at phone size | mixed alignments, a stray size, headlines that wrap badly, a line too small or too dim to read |
| `motion` | every move and every cut is intentional | R1, R4 (the card's moves, chosen by what each beat holds) | each move means something for its beat and no two beats running make the same move | the same move everywhere, a plain push on every still, or flashy moves with no reason |
| `music` | the music and the cuts agree | R5 | cuts and arrivals on the beat, the energy of the track matches the look | cuts that ignore the beat, a track at odds with the tone |
| `ending` | the reveal lands and the closer sticks | R1 payoff, an ending made to be remembered | the subject lands whole after a real tease, the name and the punchline (or a launch's date) are the last thing you read and hold still, a viewer could say them back | a reveal with no build, a line or a date that flashes past, an ending that just stops |

## The storyboards (movement 3)

For each board look at `storyboards/N/sheet.png` (and any frame full size that you need), read its
`storyboard.md`, apply the swap test below, and score it as each critic in turn in `vote/scores.json`. A
storyboard is a promise: score the film it will become, from the frames you can see. Write one paragraph per board
per critic, at least 25 words: what works, what fails, the one change you would make. The three boards are three
looks of one story; the scores say which suits this person.

### The swap test

Take each frame of the board and ask: could another photograph, another subject, another name or another date drop
into this frame without changing its design? A frame passes when its composition is made of this subject and this
person: the picture is the subject's own or a moment of theirs, picked for what it shows and where its subject sits, the type
sits where the photograph leaves room for it, their line on it is theirs, and the subject is its own still or footage.
A frame fails when it is a layout with a slot: any photograph would do under the words, the words would do on any
photograph, or the subject's name could be any subject's. Name every frame that fails in the board's paragraph. A board with one failing frame
scores `them` at most 3 and `professional` at most 4; a board with two or more scores `them` at most 2. The one change
for a failing frame says which photograph or which line the frame should be made of.

## The cut (movement 5)

The motion designer and the person score the timed cut, `film.silent.mp4`, from its strips. Before either scores,
make the reads: each is a `pass` and a `why` of at least eight words naming its seconds, in `reads` of
`critic/cut-N.json`, and a cut that fails any read never renders.

- `frame`: the picture owns the frame at every beat and the words are set into it the way the look sets them. A flat
  field waiting behind the words, or a blurred, washed or frosted copy of the photograph behind them, fails. The
  card's own grounds pass: the letterbox's bars, the grid's white page, the kinetic look's flat color under its words,
  and the closer's title on black.
- `carry`: every cut is one the look's card makes and lands on a beat of the music, and the cuts read the way the look
  promises (a cinematic look that never dissolves reads chopped, and fails).
- `sound`: a sound only where a beat lands (the hook's arrival, the build into the reveal and its impact, the last hit
  and the stop), every one under the music; read `sound` in `film.json` against the strips.
- `swap`: every move belongs to its photograph. Put another photograph under the move: a move made for this
  photograph's subject stops making sense, a slow push on any picture does not, and fails.
- `held`: one held thing per beat (the moment's photograph and their line on it), and the beat moves on once its
  words have landed; a hold past its words fails.
- `monotony`: the rhythm, below.

### The monotony read

Open `frames/film-strip.png` (the whole film at 2 fps, ten frames a row) and read `still_per_second` in
`qa/cut.json` (each second's first frame against its last, box-downscaled to 135x240, mean absolute difference;
under 0.5 the picture has locked, 1 to 5 is a slow drift, above 20 is a cut or a large move). Watch for rhythm alone, not design:

- a run of frames in the strip that look the same: the same layout, the same scale, the same place on screen, for
  more than two seconds anywhere but the closer's last two;
- every beat the same length, or the per-second line holding one level through the middle with no rise into the reveal;
- a quiet beat with no loud one after it, or a loud stretch with no quiet beat before the reveal;
- the closer complete and resting before the film's last two seconds.

Any of these is a monotony finding: set `reads.monotony` to `pass: false` with a `why` naming its seconds, name it in the
motion designer's paragraph, score `pacing` at most 3, and make the one change the lever that breaks it: a beat's length, a cut on another downbeat, a
move or an arrival placed in the stretch that stands still. A finding here is fixed before anything else in the cut.

### Then look, actually look

- `frames/strip-<beat>.png` for every beat, full size with the Read tool (12 frames across the beat);
- the hook's and the reveal's photographs against their lines: the line's verb fits what the photograph shows
  (making it over a photograph of the making, using the subject over a photograph of it in use), and every line on
  screen is word for word the subject's or theirs, true, and readable in its time;
- the stills to come: the frames `film.json` `cards` names are frames of this cut, so a beat that is wrong at rest
  is a story or a card that is wrong;
- `qa/cut.json` (the measured checks) and `render/cut-report.json`.

Never score from memory of the storyboard; the cut is what ships. Fill in `critic/cut-N.json` and run
`vote.py verdict`. When a score is below 4, name the one change that fixes the worst thing in the paragraph, using
the levers below.

## The levers

- Words, order, bars, an item's place: the winner's `storyboards/N/storyboard.json`, then `storyboard.py check`,
  `snap`, `music.py master`, `film.py cut`.
- A photograph: its subject box in `looks.json` (the crop follows it), or `skip: true` on it so the next photograph
  by the same rule plays the part, then `storyboard.py draft`, `sheets`, `check`, and the winner from `snap` on.
- A beat's line: `taste.json` `moments[].line` for its photograph (the hook's can be led by `said.hook`), then
  `storyboard.py draft`.
- The grade: `taste.json` (`palette`, `texture`), `grade.py recipe`, then `storyboard.py draft`.
- The music: `taste.json` `music` (its brief) and `music.py find`, another track at `music/source.<ext>`, or
  `music.py make --mood calm|drive|film --bpm N`, then
  `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py cut`.
