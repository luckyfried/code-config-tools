# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`; the last frame is the board's ending).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their travel palette into the film's grade (`build/grade.json`, `design/grade.md`), grades each
place's photos into `build/public/graded/`, stages the land shapes, and writes three boards that differ on how the
places are shown, on tone and on clip use:

| board | how the places are shown | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 the route | a map in their colors; the route draws itself leg by leg, a photo of theirs pinned at each arrival with the dates and the distance, then the whole map | documentary (near-black, mono labels) | still-first | an aerial opener over the first place, a flyover on the far leg |
| 2 passport | a passport page filling up: one inked stamp per place, built from that place's photos, then the full page | quiet editorial (paper, soft serif) | still-first | establishing shots of the far place and the busiest place |
| 3 day to night | the year as one long day: dawn over the first place, night near the last, then the map with every place lit | kinetic type, bold fields | clip-first (their own reels play where they were shot) | a dawn opener |

The map is drawn from the places' coordinates (Web Mercator, `build/places.json` `x`, `y`) over the shipped land
shapes; nothing is fetched. Each beat names its component (`Opener`, `ClipShot`, `MapJourney`, `Stamp`, `DayNight`,
`Poster`), its frames at 30 fps, its transition preset (`design/transitions.json`), its photos, its words, its clip
and `data.focus`, the places the beat shows. Every board also carries `poster`: the 1080×1350 map poster, laid out
by `draft` (the region's camera, an inset for a far place, each label's side so none overlap) and drawn by the same
`Poster` component in the board's palette and type. The film runs 30–60 s, longer with more places.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), put their own words about a place on its beat, fix a clip prompt that does not
fit their taste. Keep the three boards different. When a place is wrong, fix it with `places.py` (movement 1) and
run `draft` again, never by editing the board. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 30–60 s, a beat under 0.8 s, an unknown component or transition, a cut with no
transition, a beat without `data.focus`, a focus or leg that is not on the map, a place that no beat shows, a
missing poster or asset, a placeholder, a clip prompt without "no text", or more than two type faces. `sheets`
renders six frames per board with the real engine (about 15–30 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, labels that overlap, a photo cropped past its subject, colors that fight their photos, a map frame
that is mostly empty sea; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly theirs and every place in each.
