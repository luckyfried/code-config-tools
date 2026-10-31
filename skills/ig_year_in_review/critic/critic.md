# The critics

Three critics judge the storyboard (movement 3); the editor watches the timed cut and makes the four reads
before the film renders (movement 4); two of them judge the finished cut (movement 5). Each one is a voice you take on
in turn, with its own eye. Score what a viewer would notice, and say why in plain words. Every path below is inside
`build/`.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; does every photograph move; is the type a system (two faces, a scale, consistent
placement) or a default; does each move carry meaning; does anything collide, crop badly or sit outside the safe
area. Applies the swap test.

**The editor.** Cuts documentaries and social films. Looks at story: does every beat show something they did, where, or with whom,
would their friends say "that is so you", does the year build to its peak and release into the closer; does each beat earn its time; do the cuts and the sounds land on the music; does the ending
make you want to share it. Reads the timed cut with the four reads.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos, their
colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a thing?

## The seven criteria (1 to 5 each)

Each criterion scores the rules of `S/design/standards.md` it names, and a 5 is that row's "how the kit meets it" as
seen. R1 to R4 are scored from the frames and the strip and from no other evidence: not the storyboard's prose, not
the plan, not a log. R5 is scored from the four reads and the film's sound. R6 and R7 are measured by the kit's checks
and tests, never scored.

| key | scores | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | R2, R4 | every month's photograph moves under its own camera move and stands where the look puts it (full frame as a print over its own soft field, in a box of the grid, or the look's ground alone under the words); the camera gathers before each jump cut and lands on the next month's mark; eased moves, nothing collides | a photograph sitting flat while the camera moves, linear slides, an empty frame, a crop that loses the subject, a streak or a ghost of another month |
| `them` | the content rule | their photographs in calendar order carry it, and the words on screen are their own caption lines; no count and no analytics anywhere | generic stock mood, a voice that is not theirs, a number about their account, something from their avoid list |
| `pacing` | R4 | the months run two quick and one held, each holding on its moment as long as its line takes to read; the story's peak holds longest; the hook's flashes cut hard into the first month; nothing stands still over a second but the last still | uniform beats, a slow middle, a long hold on one still, two consecutive months making the same move |
| `type` | R3 | the look's two faces and its scale: the month's name and their line under it, entering the look's way (typed, slammed, cut in, risen), settled within a second; on a plate of the look's color where the ground under them needs one; inside the safe area and clear of every edge and of the subject through the hold | mixed alignments, a stray size, type that fades into what is under it, a word cut by the frame, half-typed words |
| `transitions` | R1 | the dot and its line carry every cut; each cut is one of the look's own, picked for what the beat shows; nothing stands in front of the type while it is read | the same cut everywhere, or a cut that hides the words or the title |
| `music` | R5 | cuts and sounds on the beat, the sign-off on the music's stop | cuts that ignore the beat, a sound with nothing on screen |
| `ending` | R1, R4 | the year as one image: the year's chapters, a row a month, joined by the dot, then the look's own closer landing the sign-off on the stop, then still | an ending that just stops, a closer that stands still before its line lands, rows with nothing joining them |

## The swap test (movement 3, the motion designer)

A composition is a template when another person's year would sit in it unchanged. The composition passes when their
photographs, their moments and their words move the frame (the photograph's own line the slit is cut along, their own
line for the month standing on it, the crop around what they did), and fails when the frame stays the same whatever
fills it. The passing case is a month: the slit cut along its photograph's own line, and their words for what happened
that month entering on it.

Look at the three rests on each `storyboards/<style>/sheet.png` (the hook, a month and the closer) and write the
answer in `vote/scores.json` `swap.<style>.<hook|month|closer>` as `pass` and a one-sentence `why` naming what in the frame comes
from the data. A board that fails any of the three cannot be made.

## The storyboard (movement 3)

Look at each `storyboards/<style>/sheet.png` (and any frame under its `frames/` full size you need), read its
`storyboard.md`, and score every board as each critic in turn in `vote/scores.json`. A storyboard is a promise: score the
film it will become, from the frames you can see. One paragraph per critic, at least 25 words: what works, what
fails, the one change you would make.

## The four reads (movement 4, the editor)

Before the film renders, watch `preview/film.mp4` with its strip `preview/film-strip2.png` (a 12 frames a second
strip shows the moves themselves: `ffmpeg -i preview/film.mp4 -vf "fps=12,scale=-2:300,tile=12x3" strip-%02d.png`).
The sound is the film's effects, each on a beat of the film's tempo, mixed under the music in the master `music.py
master` writes. Write `critic/timed.json`, for each read a `pass` and a `read` of at least 25 words naming the beats it
holds and fails on, from what the film shows and plays and nothing else:

- `carried`: one element is carried across every transition: the dot and its line, from the title's underline to the
  sign-off's full stop.
- `sound`: a sound where each beat lands and nowhere else, under the music: the year landing on its line, each month landing, the build into the
  peak and its impact, the closer's hit and its impact; words enter and the camera
  moves without a sound of their own.
- `swap`: the motion belongs to the photograph: the slit runs along the photograph's own line (an edge, or a visible
  alignment such as a row of heads or the eyes) and the halves hinge on it, so under another photograph the move stops
  making sense. Where the photograph has neither, a level line passes when its height visibly keeps the photograph's
  main feature whole on one side, and the read names that feature.
- `held`: one held thing per beat: the moment's photograph and their line on it, the year in the hook, the year's
  chapters at the end; and no hold over a second but the 2 s still after the stop.

`qa.py timed` stays red and `film.py render` refuses until all four pass for this cut.

## The cut (movement 5)

The motion designer and the person score the rendered film. Look, actually look:

- every `frames/<format>-<rest>.png` full size with the Read tool: the hook, a month and the closer;
- the film's strip, `qa/film-strip2.png`;
- the carousel's first and last cards and the three stories under `out/`;
- `qa/check.json` (the measured checks) and `render/film-report.json`.

Never score from memory of the storyboard; the cut is what ships. Run `vote.py cut`, fill in `critic/cut-N.json` and
run `vote.py verdict`. When a score is below 4, name the one change that fixes the worst thing, using the levers
below.

## The levers

- The moments: `taste.json` `moments` (a month's photograph, its line, the peak), then `picks.py` when a photograph
  changed, then `storyboard.py draft` and on.
- The words: `taste.json` `words`, then `storyboard.py draft`, `check`, `sheets`, the vote, `snap`, `film.py preview`
  and on.
- A month's line or scene: `picks.json` (`line`, `scene`), read from `picks-sheet.jpg`, then draft again.
- The music: another track at `music/source.<ext>`, or `taste.json` `music` and `music.py find`, then `music.py analyze`,
  `storyboard.py snap`, `film.py preview`, `music.py master`, `film.py render`.
- The layout, the crops, the type colors and the timing are computed from the moments and the photographs; they are
  never edited by hand.
