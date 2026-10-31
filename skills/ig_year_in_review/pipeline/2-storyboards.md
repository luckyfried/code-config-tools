# 2. Three looks: the film of their year, computed from their moments, in three styles

Goal: for each of the three styles, `build/storyboards/<style>/` with `board-reel.json`, `plan.json`,
`storyboard.md` and `sheet.png`; `build/storyboards/boards.json` naming them in order; and `out/boards.png`.

## Draft

```
python3 S/scripts/storyboard.py draft
```

The three styles are analog-home-movie, kinetic-type and swiss-grid; when `taste.json` `style` names a style, it is
that one and the two that differ from it most. Each board is the kit's one story told in one style card
(`S/styles/<id>.json`):

- **The hook.** The year lands on its underline the way the card brings type on (typed, slammed, cut in), and the line
  opens into a window where every month flashes, each as long as the next, up to a hard cut into the first month.
- **The months**, in calendar order whatever order `build/picks.json` lists them in: two quick months (5 beats) and a
  held one (7), the story's peak (`"peak": true` in `taste.json` `moments`) longest (10). Each month's photograph
  stands where the card's photo layout puts it: full frame as a print over its own soft field (the home movie), in a
  box of the frame on the card's ground (the grid), or not at all, the card's ground alone under the words (kinetic
  type). The month's name and their line for it come on the card's way, in the card's faces and colors, off the
  photograph's subject, inside the type area through the whole hold, and the camera gathers before each jump cut and
  lands on the next month's mark.
- **The ending.** Every month closes into its row of the year's chapters, a dot joins the rows, and the card's own
  closer lands the sign-off on the music's stop, then two silent seconds.

Every beat's move and cut is one of the card's own, picked from what that beat shows (a title, a wall, a photograph,
the peak, the ending), never by position. The colors are the ones the card's palette rule makes from their year's
palette. A month's words stand on a plate of the card's color as dense as 4.5:1 over the photograph under them needs;
each line set on the wall takes the card's ink or paper by the light of the ground under it. The handle is the
username the export's profile files give (`stats.json` `handle`), or there is none on screen; every `storyboard.py`
command refuses a stand-in handle (@you, @username, @your_handle and the like), as the handle or anywhere in the words
on screen. A year with few months makes a shorter film, never a refusal.

Each `storyboard.md` states, per beat, the moment it shows, its photograph, its move and cut, what the move reveals
and what it carries across the cut; the sound cues (a hit as each month lands, a build into the story's peak and an
impact on it, the ending's hit and impact, and the stop where picture and music end together); the music brief and
the `Mixed:` line `music.py master` fills; and the generated clips, each with its prompt, length and the move that
stands in for it.

## Check, then look

```
python3 S/scripts/storyboard.py check
python3 S/scripts/storyboard.py sheets
```

`check` refuses a board where a line of type leaves the reel's safe area at its rest, any type holds under 4.5:1 over
what is under it, a month's words cover its photograph's subject, a row's month is under 48 px or the sign-off under
72 px, a cut runs outside 6 to 90 s, or the hook lands after frame 30; and it refuses the set when two styles share
more than two of the six style axes, a board uses a face, move, cut or color its card does not have, or a board
repeats one length, one word position or one move on consecutive beats.

`sheets` renders each board's hook, a month and its ending at rest into its `sheet.png`, and the three side by side,
each under its name and one plain sentence, into `out/boards.png`. Open `out/boards.png` with the Read tool, then any
frame under `build/storyboards/<style>/frames/` that looks wrong at full size. A month's line that is not their own
words is fixed in that month's `taste.json` `moments` `line`; a sign-off that does not sound like `taste.md` in
`taste.json` `words`; a line that misses its photograph's edge in that month's `line` in `build/picks.json`; then
`draft`, `check` and `sheets` again. The layout is computed: do not edit a board by hand.

## Done when

`check` reports zero findings, the three looks on `out/boards.png` read as three different films of the same year, and
each beat's row in every `storyboard.md` names a moment they would recognize.
