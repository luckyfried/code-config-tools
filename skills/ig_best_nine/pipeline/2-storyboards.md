# 2. Storyboards: the film of their nine, computed from their numbers

Goal: the run's `storyboards/drive/`, with `board-reel.json`,
`board-square.json`, `board-wide.json`, `storyboard.md` and `sheet.png`.

## Draft

```
python3 S/scripts/storyboard.py draft --run build/<stamp>
```

`draft` builds the tone from their numbers, their dates and their photographs:

| tone | the idea | how the nine arrive | type |
|---|---|---|---|
| drive | the countdown through the wall | one continuous 3D camera: the hook's total rolls up on the top photograph and breaks into the nine counts, which gather into the three by three best-nine grid and hang there before they burst at the lens; the countdown runs from the ninth post to the first, each photograph flying onto the wall along its own line (hinged on it, sliding along it or rising square to it, in turn) and held clean for a beat, then a dot draws its own line across it and the blade cuts behind the dot; the first two and last three counts roll up onto the edge, the middle four slam onto it; the dot travels on to the next photograph with the camera; the nine stand out of the wall as bars as tall as their likes, each with its photograph and count on its face, and fold flat onto their slices into the closer, where the dot runs the countdown across the wall, landing after each count on the half beat, and comes to rest as the full stop of the ask as the handle and the ask rise; the picture and the music stop together on that hit and the wall holds silent | kinetic: extruded condensed numerals |

Every board is the storyboard the studio composition (`S/motion/studio`) renders: the rank order, the layout (the
cuts and their edges), the words, and each photograph by its
focus point and square crop. One storyboard is solved three times, for the reel (1080x1920), the square
(1080x1080) and the wide (1920x1080): a tile that fits the reel is placed again for the square, never scaled to fit.
Each board names its rests, the settled frames the sheet, the critics and the stills read: the hook, the densest
beat and the closer, and for drive an ordinary count beat. With fewer than nine posts, the board lays out the ones there are.

The drive board also carries, per scene, what its move reveals and what it carries across the cut; the sound cues
(`sound`: a riser into the hook, hits where counts land and edges cut, ticks under each roll, a whoosh panned with
each camera travel, an impact on the closer, a light hit each time the closer's dot lands after a count, and the stop
where the picture and the music end together), each at its named beat; and the generated clips (`clips`: the wall's
world under the hook, each photograph brought to life under its count beat, the texture under the bars), each with
its prompt, length, photograph and the camera or depth move that stands in for it. `storyboard.md` states all three
as tables.

## Check, then look

```
python3 S/scripts/storyboard.py check --run build/<stamp>
python3 S/scripts/storyboard.py sheets --run build/<stamp>
```

`check` runs the bounds check on every format at every rest and every beat's settled frame. It refuses a board
where a photograph is cropped by the frame, sits behind another, or loses its gutter from the frame edge or the
type band; where type leaves its safe area, a tag hides a count, a count is set under the tone's floor, or a strand
leaves its square runs; and a cut outside the length band (15 to 30 s for nine posts) or a hook event after frame
30. Each `storyboard.md` states the board's cuts and cuts per minute, a figure for the critics. `sheets` renders each
tone's three rests in the three formats into `sheet.png` with the real composition.

Open each `sheet.png` with the Read tool, then any frame under `storyboards/<tone>/frames/` that looks wrong at full
size. A line that does not sound like `taste.md` is fixed in `taste.json` `words.<tone>`; then `draft`, `check` and
`sheets` again. The layout is computed: do not edit a board by hand.

## Done when

`check` reports zero findings and the sheet looks clearly theirs.
