# The critics

Three critics judge the storyboard (movement 3); the editor makes the timed read of the previewed reel before it
renders (movement 4); two of them judge the finished cut (movement 5). Each one is a voice you take on in turn, with
its own eye. Score what a viewer would notice, and say why in plain words. Every path below is inside the run,
`build/<stamp>/`.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the motion eased and
layered or does it slide; do the photograph, its ground and the wall move at different rates; is the type a system
(two faces, a scale, consistent placement) entering word by word, or a default; does each move carry meaning; does
anything collide, crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does the first second say what the reel is;
does each card carry one idea and only one; does the reel walk the month's diary from the peak that opens it,
through each other moment once in date order, to the wall of the month's posts in the closer, where every moment
lights; does each beat earn its time and the peak hold longest; do the cuts land on the music and the music stop at
the ask; would you watch the reel and tap through every card to the end.

**The person.** Speaks in the first person, from the run's `taste.md` and their captions: "is this me?" Their
photographs, their words, their people and places, their pacing, nothing on the avoid list. Would I post this today,
without changing a thing? The person breaks a tie in the storyboard vote.

## The seven rules (1 to 5 each)

Each rule scores the film against its row of `S/motion/system/standards.md`: a 5 meets the row in every frame you look at,
a 4 misses it in one beat, a 3 or lower misses it across the film. Name the frame (its time) a low score reads. A
rule nobody in the session can read is scored `"not read"` and the paragraph says why; it never counts as meeting
the rule.

| key | rule | a 5 | a 3 or lower |
|---|---|---|---|
| `R1` | one concept | the first second says "my <month>, in N stories"; the line rises across every photograph and runs under the wall; the closer lights every moment on the wall; every move between beats is the one camera travelling along the line, never a crossfade | a hook with no idea in it, a beat that does not show its moment, a payoff that lights fewer moments than the words promise, the same zoom between every beat |
| `R2` | image treatment | through each hold the photograph moves against its band and the camera, its edge wrapped in the ground's light and shading the photograph under it, a shadow under every card lifted off the wall, grain over all, one grade on every photograph; the closer's still is still | a flat photograph on a plain push, a hard unlit edge, photographs that do not match in color |
| `R3` | type in motion | two faces on one scale; every line enters word by word, each word's tracking closing as it lands, and leaves the same way, never a fade; every line settled within a second of its beat; every line inside the safe area through the hold; nothing crosses a word | lines that fade or slide in whole, a line pushed past the side margins, the line or the dust over a word, a stray color for the same field |
| `R4` | motion and rhythm | one camera that backs off before each move and lands a little past where it stops; the camera moves differently through each hold, never the same way two holds in a row; the peak holds longest; the closer holds still and silent at least a second after the ask | uniform beats, the same push on every card, a move that starts and stops dead, a closer that ends as the ask lands |
| `R5` | sound to picture | one cue where each beat lands and nowhere else; the effects 8 LU under the music; the music stops where the ask lands | a cue on a word or a move, effects over the music, music running past the ask |
| `R6` | generated shots | every clip request is a shot a cinematographer would write from its photograph: its subject, the camera's move, the lens, the height, the light, the beat's length and a seamless loop, the first the hook's world | requests that say the same thing, a request with no lens or light, a subject that is not in the photograph |
| `R7` | the deliverable | `out/` holds the films, the cover, the cards, the caption and the review page, which opens on the reel with its cover and nothing a viewer could mistake for the product | a storyboard sheet or a working file in `out/`, a review page with no cover, card headers that do not match |

## The storyboard (movement 3)

Look at each of the run's three boards, `storyboards/<style>/reel-sheet.png` and `sheet.png` (and any still full
size that you need, in its `reel/` and `rest/`), read its `storyboard.md`, and score each as each critic in turn in
`vote/scores.json`. A storyboard is a promise: score the film it will become, from the frames you can see and the
beats it lists. Write one paragraph per critic, at least 25 words: what works, what fails, the one change you would
make.

## The timed read (movement 4)

The editor reads the winning look's `storyboards/<style>/storyboard.md`, watches `preview/film.mp4`, looks at `preview/film-strip.png`
and `film-strip2.png`, and writes the four reads in `critic/timed.json`. Each read is `true`, `false` or `"not
read"`, with at least 25 words on where it holds and where it does not, or on why nobody in this session can make it
(a session that cannot hear the sound says so for `sound` and reads the storyboard's sound lines and Mixed line
instead):

- `carried`: one element is carried across every transition. The line goes from the first moment into every other and
  under the wall in the closer; each photograph sets into its post's cell on the wall of the month's posts the closer
  shows, its day beneath it. A cut where nothing comes through fails.
- `sound`: a sound where each beat lands and nowhere else, under the music. A beat that lands with no sound, a sound
  on a word or a move, or an effect over the music fails.
- `swap`: the motion belongs to the photograph. Put another photograph under the same move: the line climbs this
  photograph to above its subject, the camera holds about what it shows, their words sit under it. A move that would
  make the same sense under any picture fails.
- `held`: one held thing per beat, the moment's photograph and its line, and no beat holds longer than its words
  need. A frame where a field of color is the stage fails.

`film.py render` needs the four reads made for this board and prints any that did not pass; it renders the board all
the same, and the gate states each read.

## The cut (movement 5)

The motion designer and the person score the rendered reel, the series and every card on the seven rules. Look,
actually look, at the files this render wrote:

- `out/film.mp4`;
- `timeline/film-strip.png`, `film-strip2.png` and (when the series is made) `series-strip.png` full size with the
  Read tool;
- every still in `out/cards/NN-story.png` and `out/cover.png`;
- `qa/check.json` (the measured checks, rerun after every render, and the two figures, cuts and still),
  `render-report.json` and `clips/requests.json`.

Score R2 and R4, like every rule, only from what these frames and strips show, never from memory of the cut before;
the cut is what ships. Fill in `critic/cut-N.json`
and run `vote.py verdict`. A round after the first says in `fixed` what changed and reads the new render's frames:
no paragraph repeats the round before.

## The verdict

Each rule stands at the lower of the two critics' scores. The bar is a mean of 4.5 over the seven rules with none
under 4 (`vote.py` BAR). `vote.py verdict` prints one of three:

- `AT THE BAR`: deliver.
- `FIX ONCE`: after the first cut, the lowest rule under the bar that the agent has a lever for. Make that one change
  with the lever below and run the movements it names again.
- `SPENT`: the fix is made (or no rule under the bar has a lever). Deliver this cut as the best one: `brief.md`
  states every score against the bar, and the review page shows none. A score under the bar never blocks the render or
  the delivery.

## The levers

- `R1`: `taste.json` `moments`, the moments and the line each says on screen.
- `R3`: `taste.json` each moment's line, shorter so it sets larger and breaks cleanly.
- `R4`: `taste.json` which moment is the peak and the line each moment holds for.
- `R5`: `taste.json` `music`, the styles they named and what the bed leaves out.
- `R6`: `taste.json` `moments[].shot`, each shot written again as a cinematographer would write it from its
  photograph.

`R2` and `R7` are the motion system's and the kit's own; the agent has no lever for them, and a score under the bar
on either is spent. After any lever, run movement 2 again (`storyboard.py draft`, `check` and `sheets`, the vote),
then movement 4 (`music.py make`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed`, `film.py
render`), then `vote.py cut` for round 2.
