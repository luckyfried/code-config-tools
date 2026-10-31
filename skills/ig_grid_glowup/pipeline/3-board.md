# 3. Boards: the same story in three looks, and the look they pick

Goal: three storyboards (`storyboards/A`, `B` and `C`), their sheets side by side in `out/boards.png`, and the one
picked: `board.json`, `winner.json` and `storyboard.md` in the run folder.

## Draft

```
python3 S/scripts/storyboard.py draft
python3 S/scripts/storyboard.py sheets
```

`draft` reads the grid research read (`grid.json`), the plan and `taste.json`, grades the plan's photos with their
grade (`grade.json`, `design/grade.md`) into `public/`, and writes three boards. The story is the same in all three:

- the hook lands on their grid as it is, with the line that states the glow-up;
- the posts that break their first screen are found, and the next posts drop into the grid one by one, each as the
  moment it shows in the words it came with (else its caption), the middle one held longest;
- the closer is their profile's first screen with the nine in place, their handle and their bio as they wrote it
  (emoji and line breaks kept), and picture and music stop together. No count and no date is on screen.

What differs is the look. Each board is the story set in one style (`styles/<id>.json`): its faces and their case,
its colors over their palette, its easing and finish, its camera pace, the move each beat makes (chosen from what the
beat shows, within the style's moves), the caption's entrance and the closer's shape. Board A is the style
`taste.json` names (`style`, from their type direction); B and C are the two styles that differ most from it.
`--style <id>` puts any style on A. Each board is drafted at its own music's tempo, from its style's recipe.

`draft` refuses a board whose words do not fit: a line past its band, a line sitting on another, a line meant to be
read outside the format's type area at the camera's rest on it, or under a 40 px cap height on screen (it must read on
a phone held at arm's length). Each fault names the board, the format, the beat and the line. A post's words are their
own and never cut: when the words a photograph came with do not fit, set a shorter line of theirs for it in
`taste.json` `"said"` (pipeline/2-plan.md) or plan another photograph in its place, and draft again.

`sheets` renders each board's settled frames (the hook with its words, the densest post, the closer) with the
composition the film uses into `storyboards/<L>/sheet.png`, and the three side by side into `out/boards.png`.

## Look

Open `out/boards.png` and each `storyboards/<L>/storyboard.md` with the Read tool. Ask: does a word run out of its
place, does a photograph sit on its subject, does every post carry its own words, do the three looks read as three
different hands with the photos covered. Fix the plan and draft again; never edit a board file.

## Done when

`draft` prints that bounds and the type floor hold for all three boards, and `out/boards.png` is there.
