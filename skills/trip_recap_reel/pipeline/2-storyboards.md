# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`; the last frame is the board's ending on the whole route).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns the trip's palette into the film's grade (`build/grade.json`, `design/grade.md`), grades the trip's
photos into `build/public/graded/` and writes three boards that differ on structure, tone and clip use:

| board | structure | tone | generated clips |
|---|---|---|---|
| 1 the route | day by day in order; each day's photos with the map thread inset, the route so far and today's leg drawing; ends on the whole route | documentary (near-black, mono labels) | an establishing shot to open and a map flyover; their own clips sit in their days |
| 2 the mood | place by place cut to the music, photos on the beat, one heavy word per place | kinetic type, bold fields | clip-first: weather and texture b-roll between places, their own clips |
| 3 postcards | one postcard per place: their photo as a print, their own caption set as type, a stamp with the place and the day | quiet editorial (paper, soft serif) | an establishing shot of each place before its postcard |

Each beat names its component (`Opener`, `Route`, `Day`, `Montage`, `Postcard`, `ClipShot`, `Closer`), its frames
at 30 fps, its transition preset (`design/transitions.json`), its photos, its words, its data (the route's points
from `trip.json`, the stretch drawn in this beat, the stamp) and its clip. The same board renders the 9:16 film and
the 16:9 film. Every board also carries `stories`: five 1080×1920 cards (the opener, three places, the closer) in
the board's palette and type.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), choose a better caption of theirs for a postcard, fix a clip prompt that does
not fit their taste. Keep the three boards different and keep every place of the trip in each. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 30–60 s, a beat under 0.8 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", a map beat with no route points, a place of the trip that no beat
names, or a board without five story cards. `sheets` renders six frames per board with the real engine (about 10
to 25 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a photo cropped past its subject, colors that fight their photos, two map labels on top of each
other; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly their trip.
