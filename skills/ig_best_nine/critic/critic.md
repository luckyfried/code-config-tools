# The critics

Three critics judge the three looks' storyboards when the panel picks (movement 3); the editor reads the timed cut before it renders (movement 4);
two of them judge the finished cut (movement 5). Each one is a voice you take on in turn, with its own eye. Score
what a viewer would notice, and say why in plain words. Every path below is inside the run, `build/<stamp>/`.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photograph move; is the type a system (two faces, a scale, consistent
placement) or a default; does each move carry meaning; does anything collide, crop badly or sit outside the safe
area. Applies the swap test.

**The editor.** Cuts documentaries and social films. Looks at story: does every beat show something they did, and
would their friends say "that is so you"; does the countdown build to the first; is there a turn, a peak and a
release; does each beat earn its time; do the cuts land on the music; does the ending make you
feel something and want to share it. Reads the timed cut for monotony.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos, their
colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a thing?
The person breaks a tie in the storyboard vote.

## The seven criteria (1 to 5 each)

Each criterion scores the film against the rows of `S/motion/system/standards.md` it names: a 5 meets every one of
those rows in every frame you look at, a 4 misses one in one beat, a 3 or lower misses a row across the film. Name the
row a low score misses.

| key | criterion | scored against | a 5 | a 3 or lower |
|---|---|---|---|---|
| `professional` | it looks like a professional motion designer made it | R2, R4 | studio grade: every photograph moves, sits in the look's finish (its grade, grain, rim or bars), and nothing collides or crops past its subject | flat photographs on a plain push, photographs that do not match in color, a crop that loses the subject |
| `them` | it is unmistakably them | the swap test, R2 | their nine carry it whole: their photographs, their words, their days | generic stock mood, a voice that is not theirs, something from their avoid list |
| `pacing` | the pacing holds attention to the end | R4 | a rhythm with variation; the first holds longest; quiet beats earn the loud ones; the closer holds still | uniform beats, a slow middle, a long card with one word |
| `type` | type is a system, not a default | R3 | the look's two faces at a scale, one placement logic per layout, every line landed within a second and read in full | a stray size, a line that wraps badly, words on a ground they do not read on, a line outside the safe area |
| `transitions` | every move between beats is intentional | R1, R4 | each cut and move is the look's own; anticipation before a big move and a settle after it; no two beats in a row move the same way | the same crossfade everywhere, the same push on every beat, flashy wipes with no reason |
| `music` | the music and the cuts agree | R5 | the bed belongs to the look, cuts land on its beat, the music stops as the grid settles | cuts that ignore the beat, a track at odds with the look |
| `ending` | the ending makes them want to post it | R1, R7 | the countdown lands on their first, the grid of all nine holds still, the closer signs off in the look's own type | an ending that just stops, a layout that never resolves, a generic sign-off |

## The swap test (movement 3, the motion designer)

A composition is a template when another person's year would sit in it unchanged. It passes when their posts decide
what fills the frame: each photograph cut to its own subject, the order from their likes, each day and line their
own. It fails when the content stays the same whatever fills it: a decorative frame, words that would caption
anyone's photograph, a crop that ignores the subject.

The three by three grid of the posted image is the standard, never a reason to fail: it is the best nine as a person
posts it, and the film resolves into it. Whatever the composition, three checks stay: all nine are present, each is
legible at its size, and every one is the person's own content.

For each look, take its three rests on `storyboards/<style>/sheet.png` (the hook, the densest beat and the closer)
and write in `vote/scores.json` `swap.<style>.<hook|dense|closer>` `pass` and a one-sentence `why` naming what in the
frame comes from their nine. A look that fails any of the three cannot win the tally.

## The three looks (movement 3)

`out/boards.png` shows the three looks, A, B and C, each by its hook, a middle beat and its closer. When the person
picks, their answer is the look (`vote.py pick --board`). When nothing may be asked, the pick is by taste with a
one-line reason (`--why`). The panel scores the three only when asked to choose for them: open each
`storyboards/<style>/sheet.png`, read its `storyboard.md`, and score it as each critic in turn in `vote/scores.json`,
one paragraph per look per critic, at least 25 words: what works, what fails, the one change you would make.

## The timed cut (movement 4, the editor)

Before the film renders, open `preview/film-strip2.png` (the cut at two frames a second) and, when a moment needs
it, `preview/film.mp4`. Read it for monotony: do neighboring beats change layout and size, does the rhythm vary, does
each beat move its own way? `preview/preview.json` carries the cuts per minute and the luma line; they are evidence,
never a verdict. Write `critic/timed.json` `monotony.pass` and a paragraph in `monotony.read` naming the beats you
mean. A cut that repeats one layout, one move in a row, one length or one place for the words fails `qa.py timed`'s
template check however clean each frame is, whatever this read says; `film.py render` refuses until both pass.

## The cut (movement 5)

The motion designer and the person score the rendered film. Watch `out/film.mp4` at full size, once through, the
way a paying client would, then look at:

- every `frames/<format>-<rest>.png` full size with the Read tool;
- the film's strip, `qa/film-strip2.png`;
- `out/best-nine.png` (all nine shown, nothing cropped badly, the order reads);
- `qa/check.json` and `render/film-report.json`.

Never score from memory of the storyboard; the cut is what ships, and a score is never rounded up. Fill in
`critic/cut-N.json` and run `vote.py verdict`. The film ships at the bar: a mean of 4.5 or more with no criterion
under 4. Under it, the one fix names the change to the worst thing, through the levers below, and the film renders
again. A film still under the bar after that fix is delivered as the best cut, with its scores in the run's
`brief.md`; the review page never shows a score.

## The levers

- A beat's layout, move and length: `taste.json` `beats.<beat id>` with `layout`, `move` (one of the look's moves)
  or `seconds`, then `storyboard.py draft`, `check`, `sheets`, `vote.py pick`, the music and on.
- The words: `taste.json` `words`, the same steps.
- The music: another track at `music/source.<ext>`, or `taste.json` `music`, then `music.py find`, `storyboard.py
  snap`, `film.py preview` and on.
- The crops and the timing within a beat are computed from their photographs, captions and dates; they are never
  edited by hand.

Every `storyboard.py draft` takes away the pick (`winner.json`) and the panel's scores, because the pick was made on
the sheet that was shown; `snap` cuts only a board with a pick.
