# 2. The storyboards: one story in three looks, laid out from the posts

Goal: three boards, `RUN/storyboards/<style>/` for each of the run's three looks, each with `storyboard.json`,
`storyboard.md`, its styleframes (`frames/hook.png`, `ordinary.png`, `dense.png`, `closer.png`, `end.png`) and
`sheet.png`; `RUN/out/boards.png`, the three side by side; and no finding in `RUN/storyboards/check.json`.

A look is a style card, `S/styles/<style>.json` (`S/styles/catalog.md` says what each looks like): its two faces, how
its colors are made from their photographs, the moves and cuts it may use, its easing, its finish and its closer. The
three looks are cinematic letterbox, editorial quiet and kinetic type, in that order (A, B, C), or, with `style` in
`RUN/taste.json`, that look first and the two that share the fewest traits with it. The story is the same in all
three; everything about how it looks comes from the card.

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` is the board builder. It reads the posts (`RUN/subject.json`) and lays out everything the film shows and
places: day one and the latest post, the milestones, the line curated for every photograph in `RUN/taste.json`
`moments` (matched by the photograph's path), their own words for the span (`said_span`) or their two dates,
and for every photograph its station (where it fills the frame), its tile on the wall and the window onto the
photograph each shows, framed about its point of interest. Nothing on screen is typed by hand: the words are their
curated words, the ask is the call to action they asked for (`call_to_action`) or else their handle, and the only
numbers are the dates they posted on, a number in their curated words and in the call to action they asked for.

**The concept, their story in their words.** One camera walks the wall their posts build, from day one to the latest,
in chapters told in their own captions. The wall is there from the first frame: a wall in the look's ground with a tile for every
post in calendar order, in bands the camera walks one way and then back, under one plain course of plaster across its top
where the closer's words are set, which no print's station frames; day one opens the first band and the latest closes the last, each four cells large, and
the posts the camera has not reached stand dim. At each post its print lifts out of its tile toward the lens: the
photograph at its own proportions (cropped about its point of interest only when it is taller or wider than the card
allows), set as the look's card sets a photograph, with its date and their line in the look's faces. It lands a little past its rest and settles, stands off the wall with its shadow under it and
light wrapping its cut edges, while the photograph inside the border pushes in and moves against it. Their line
enters as the look's type enters, and is read before it leaves. When the
camera moves on, the words leave letter by letter, the print drops into its tile, and the camera travels along the
wall to the next post, winding back before it goes and landing past its mark. Each move is one the look allows, chosen by what the beat holds (a portrait or a landscape photograph,
a chapter, the step it crosses on the wall), never the same move twice running, and the cut into each beat is one of
the look's own cuts. Day one, every milestone and the latest are the chapters: their line lands harder and their next
line rises under it (their own words for the moment, under the date), and they hold longest, the peak (the
last milestone, else the latest) longest of all. Every beat holds as long as its photograph carries: longer for more
words, a wider or busier scene, or a bigger change from the photograph before, shorter for a photograph that repeats
the one before, and never shorter than its words take to read once they have landed. The closer is the look's own
closer (a title card, a caption alone, a build of letters) over the wall they built, and sets their own words for the span
("fourteen months in") over their two dates, or their first and latest dates alone when no caption says it; a line
that only repeats those words gives way to its next line, so the span is said once. Last the ask, the call to action
they asked for or else their handle, lands under the dates; picture and music stop as it lands and the wall holds,
silent.

**The length.** With `seconds` in `RUN/taste.json`, every hold scales together until the film runs that long, each
still between the least its photograph needs and the most it can hold; without it the film runs at its own pace.
`draft` prints the range the set makes well. An ask outside it is made at the nearest end of the range, and draft
prints one plain line with the length made and why ("You asked for 45 s; these 4 photographs carry at most 28.2 s, so
the film is 28.2 s."). A set that needs more than 60 s is not delivered: draft prints `not delivered: `, exits 2 and
writes no board. When every line read at its least would run past 60 s, ordinary posts pass over their date alone,
their line left off, and draft prints one plain line naming them; day one, the milestones and the latest keep every
word. Curate fewer lines in `RUN/taste.json` to choose which posts keep theirs.

`storyboard.md` says, per beat, its photograph, their line on it, what the move reveals and what it carries across the cut, carries the music brief,
lists the sound cues where each beat lands, and lists the clips an image-to-video model would make with the camera move that stands in for each. The
board is laid out for the reel (9:16) and again for square and wide from the same posts, each format's wall and
type solved for its own frame.

A post without a date is left out and named in `storyboard.md`. Fewer than two dated posts, or every post on one
day, is no before and after: draft exits 2 with the sentence to tell the person, and writes no board.

## Check and render the styleframes

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` runs the builder's rules on the board in every format: a line meant to be read under 28 px cap height on
screen (at its card's station or on the closer's wall), type outside the format's safe lines or nearer its print's
edge than its inset, type on a photograph instead of its label, a print that covers its frame edge to edge, a frame
that shows past the wall's edge, closer type off the course, a number on screen that is not a date or a number in
their curated words, and a hook with no event in its first 30 frames; and across the three boards, two looks that
share more than two traits. `sheets` renders each board's rest moments, then each board's sheet, then
`RUN/out/boards.png`: one row per look, its opening, its busiest moment and its ending, its name and one plain
sentence under them. A new `draft` removes the old boards' sheets and styleframes, and `vote.py ballot` refuses a
board with no sheet.

## Look at the styleframes

Open `RUN/out/boards.png` and each `RUN/storyboards/<style>/sheet.png` with the Read tool, then each styleframe full size. Read `storyboard.md`
beside it: the beats, the photographs, their lines, the sound and what each move carries.

The board is not edited by hand; a fault in a frame is a fault in the posts the builder read. A wrong subject, a
milestone their words do not support, a post that is not theirs, a caption that says something the photograph does
not show: fix the research or the captions at their source (`research.py --subject "..."`) and run `draft`, `check`
and `sheets` again.

## Done when

`check` reports no finding, each board's styleframes read as one film that is clearly theirs, and the three looks
read as three different films of the same story.
