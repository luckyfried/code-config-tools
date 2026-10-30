# 2. Storyboards: the nine in three looks

Goal: three storyboards of the same film, one per look, each in `storyboards/<style>/` (`board-reel.json`,
`board-square.json`, `board-wide.json`, `storyboard.md`, `sheet.png`), and `out/boards.png`, the three side by side.

## Draft

```
python3 S/scripts/storyboard.py draft --run build/<stamp>
```

The three looks are three style cards in `S/styles/` (`S/styles/catalog.md` says each in a sentence): Swiss grid,
Scrapbook and Cinematic letterbox, or, when `taste.json` `style` names one, that look and the two that differ most from
it. Each look takes its faces, colors, easing, finish, moves, cuts, closer and music from its card and from nowhere
else.

The story is the same in all three. It opens on the first of the countdown, full in the frame, with their title over
it. Then the nine, from the ninth to the first, with no number on screen: each in a layout of its own (nine layouts for
nine posts), the photograph placed by its focus, their caption line and its day set in the look's faces, moved by one
of the look's moves and cut into with one of its cuts, no move twice in a row. Then the nine as they post them, a three
by three grid, the first at its top left, with the year and the ask; and the look's closer with their title and their
promise, held still as the music stops.

Each beat holds as long as its post asks: a captioned post for its words, a wordless one less, a repeat least, and the
first longest. The film runs the length asked (`taste.json` `seconds`, 20 to 45 s, 30 s when it is `null`); a length
outside that makes nothing and prints `not made: ...`, the sentence to pass on. A year with fewer than nine posts with
a photograph prints `not delivered: <n> posts, nine needed`.

One storyboard is solved three times, for the reel (1080x1920), the square (1080x1080) and the wide (1920x1080).
`storyboard.md` states each board's beats, cuts, sound cues and the generated clips it would use.

## Check, then look

```
python3 S/scripts/storyboard.py check --run build/<stamp>
python3 S/scripts/storyboard.py sheets --run build/<stamp>
```

`check` refuses a board where a photograph is cropped by the frame or sits behind another, type leaves its safe area
or overruns its box, the cut is more than 1 s off the asked length or the hook lands after frame 30, and any template
tell: a layout used twice, one move on two beats in a row, every shot one length, the words in one place, or anything
the card did not give. `sheets` renders each look's hook, a middle beat and its closer into its `sheet.png`, and the
three into `out/boards.png` with each look's name and one sentence.

Open `out/boards.png` and each `sheet.png` with the Read tool, then any frame under `storyboards/<style>/frames/` that
looks wrong at full size. A line that does not sound like `taste.md` is fixed in `taste.json` `words` or `moments`;
then `draft`, `check` and `sheets` again. The layout is computed: never edit a board by hand.

## Done when

`check` reports zero findings for the three looks and `out/boards.png` shows three looks that are clearly theirs.
