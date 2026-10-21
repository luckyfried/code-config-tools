# The critics

Three critics judge the storyboards (movement 3); the editor reads the timed cut before it renders (movement 4);
two of them judge the finished cut (movement 5). Each one is a voice you take on in turn, with its own eye. Score
what a viewer would notice, and say why in plain words. Every path below is inside the run, `build/<stamp>/`.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photograph move; is the type a system (two faces, a scale, consistent
placement) or a default; does each move carry meaning; does anything collide, crop badly or sit outside the safe
area. Applies the swap test.

**The editor.** Cuts documentaries and social films. Looks at story: does the build to number one land; is there a
turn, a peak and a release; does each beat earn its time; do the cuts land on the music; does the ending make you
feel something and want to share it. Reads the timed cut for monotony.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos, their
colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a thing?
The person breaks a tie in the storyboard vote.

## The seven criteria (1 to 5 each)

| key | criterion | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | studio-grade: eased, layered, nothing collides | template feel, linear slides, text over a busy photo, a crop that loses the subject |
| `them` | it is unmistakably them | their nine carry it whole, their words, the numbers and dates that made these nine | generic stock mood, a voice that is not theirs, something from their avoid list |
| `pacing` | the pacing holds attention to the end | a rhythm with variation; quiet beats earn the loud ones; no beat outstays itself | uniform beats, a slow middle, a long card with one word |
| `type` | type is a system, not a default | two faces, a scale, the same placement logic everywhere | mixed alignments, a stray size, headlines that wrap badly |
| `transitions` | every move between beats is intentional | each one is the tone's own act (the edge pivoting to the next photograph's line, a string arriving, a tub rising) | the same crossfade everywhere, or flashy wipes with no reason |
| `music` | the music and the cuts agree | cuts on the beat, the energy of the track matches the film's | cuts that ignore the beat, a track at odds with the tone |
| `ending` | the ending makes them want to post it | the nine land together as the last image, every one shown, one they would screenshot; the story card invites a reply | an ending that just stops, a layout that never resolves, a generic sign-off |

## The swap test (movement 3, the motion designer)

A composition is a template when another person's nine would sit in it unchanged. Swap one photograph for another
post and the post brings its own numbers with it: its rank, its likes, its date. The composition passes when those
numbers move the frame (where the post sits in the order, how big it is, the count it carries, the string from its
day), and fails when the frame stays the same whatever fills it: fixed slots with no numbers in them, a decorative
frame, words that would caption anyone's photograph.

The passing case to measure against is the drive tone's closer: the nine as an even 3x3 grid, in rank order, each
square carrying its own likes. It is the best nine itself, and it passes, because another person's nine reorders the
squares and changes every count on them. Sizing a tile by its likes, routing a string from its date and raising a
tub to its count pass for the same reason.

For each board, look at its three rests on `sheet.png` (the hook, the densest beat and the closer) and ask of each:
would a different nine, with their own numbers, change this frame? Write the answer in `vote/scores.json`
`swap.<tone>.<hook|dense|closer>` as `pass` and a one-sentence `why` naming what in the frame comes from the data. A
board that fails any of the three cannot win the vote.

## The storyboards (movement 3)

For each tone look at `storyboards/<tone>/sheet.png` (and any frame under its `frames/` full size that you need),
read its `storyboard.md`, and score it as each critic in turn in `vote/scores.json`. A storyboard is a promise:
score the film it will become, from the frames you can see. Write one paragraph per board per critic, at least 25
words: what works, what fails, the one change you would make.

## The timed cut (movement 4, the editor)

Before the film renders, open `preview/film-strip2.png` (the cut at two frames a second) and, when a moment needs
it, `preview/film.mp4`. Read it for monotony: do neighboring beats change size (wide, close, macro), does the
rhythm vary, does a repeated layout still change as it builds? `preview/preview.json` carries two figures to read
beside the strip, the cuts per minute and the luma line (the seconds under 0.5 are the quiet ones); they are
evidence, never a verdict: a held composition is quiet by design, and a busy cut can be a template. Write
`critic/timed.json` `monotony.pass` and a
paragraph in `monotony.read` naming the beats you mean. A read that fails names the beat that repeats; `qa.py timed`
stays red and `film.py render` refuses until a cut passes.

## The cut (movement 5)

The motion designer and the person score the rendered film. Look, actually look:

- every `frames/<format>-<rest>.png` full size with the Read tool: the hook, the densest beat and the closer of the
  reel, the square and the wide;
- the film's strip, `qa/film-strip2.png`;
- `out/best-nine.png` (1080x1080: all nine shown, nothing cropped badly, the order reads) and `out/story.png`;
- `qa/check.json` (the measured checks) and `render/film-report.json`.

Never score from memory of the storyboard; the cut is what ships. Fill in `critic/cut-N.json` and run `vote.py
verdict`. When a score is below 4, name the one change that fixes the worst thing in the paragraph, using the
levers below.

## The levers

- The words: `taste.json` `words.<tone>`, then `storyboard.py draft`, `check`, `snap`, `film.py preview` and on.
- The tone: `storyboard.py snap --board <tone>` cuts another board, then `film.py preview` and on.
- The music: another track at `music/source.<ext>`, or `music.py make --mood calm|drive|film --bpm N`, then
  `music.py analyze`, `storyboard.py snap`, `film.py preview`, `music.py master`, `film.py render`.
- The layout, the crops and the timing are computed from their numbers and photographs; they are never edited by
  hand.
