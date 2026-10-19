# 2. Storyboards: three different films of the same guide

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the film's grade (`build/grade.json`, `design/grade.md`), grades the photos the
film uses into `build/public/graded/`, builds the ten guide cards from `build/brand.json` (palette, type,
compositions, voice with three real captions, pillars, cadence, aspire, stop, statement, first week) and writes
three boards that differ on how the guide is shown, on tone and on clip use:

| board | how the guide is shown | field and tone | generated clips |
|---|---|---|---|
| 1 one card at a time | a reel that reveals the cards one by one, the statement held longest | dark, bold | the opener and a bridge between the two halves |
| 2 the swipe | a guide you swipe, the cards on one grid, five and five | paper, calm | the opener and the turn, from their photo |
| 3 the poster | one poster of all ten panels; the camera reads it panel by panel and pulls back | their lead color, cinematic | the opener and the world behind the poster |

The cards are set in the brand's own type direction and palette on every board. Each beat names its component
(`Opener`, `ClipShot`, `Reveal`, `Swipe`, `Poster`), its frames at 30 fps, its transition preset
(`design/transitions.json`), its photo or cards, its words and its clip.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none); change a card's words in `brand.json` through `taste.json` and
`brand.py system`, never on one board only. Fix a clip prompt that does not fit their taste. Keep the three
boards different. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 20–30 s, a beat under 0.8 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", cards that are not the ten in order, a voice card without three
real captions, a week card without seven days, or a film that does not show every card exactly once. `sheets`
renders six frames per board with the real engine (about 30 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides or wraps badly, a card photo cropped past its subject, colors that fight each other, a card that
reads empty; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly their brand.
