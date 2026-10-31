# 2. Storyboards: their month's diary in three looks, composed from their moments, their words and their photographs

Goal: three boards, one a look, each in the run's `storyboards/<style>/`: `storyboard.json`, `storyboard.md`, the reel
sheet (`reel-sheet.png`) and the rest sheet (`sheet.png`), every board check green and every sheet with no finding;
and `out/boards.png`, the three looks side by side. The looks are the trio `editorial-quiet`, `scrapbook` and
`swiss-grid`; when they name a look (`taste.json` `style`), or last month's template carries one, that look and the two
of the trio that differ most from it. A look is its style card's faces, palette rule, moves, cuts, closer, pace and
music; the story is the same in all three.

## Draft

```
python3 S/scripts/storyboard.py draft
```

The board builder (`S/scripts/compose/`) composes the run's `month.json` and the moments picked in `taste.json` into
the board: the reel (`compose/reel.py`) and the story cards, one of 15 s a moment on the same 3D system
(`compose/stories.py`). Every size, position and time is computed from their photographs, their words and their days.
The board carries their `ask` from `taste.json`: with `counts`, every moment's card shows that post's likes and comments
under its photograph, as `month.json` carries them, each counting up from zero as its line rises in (and without `counts` no
number of theirs is on screen); with `seconds`, the reel runs that length to the frame; with `series`, the cards are
also made as one video. The kit makes a reel of 12 to 30 s: a `seconds` outside that range is refused before anything
is touched, with "not delivered: this kit makes a reel of 12 to 30 s, and the ask is for N s. Ask for a length in that
range." (exit 2, nothing made); tell the person that line and stop. A moment with no photograph is a type card: its words (or its count,
with `counts`) set big in the display face on the ground every card shares, and the camera and the line move over the
type as they would over a photograph. `storyboard.py draft` prints each look and how long its reel runs against the
length asked.

The look is the person's when they give one: `--template FILE`, else `template.json` in the workspace, else last
month's `build/template.json`. Its palette sets the ground (the plates under the words, the type cards' field), the ink,
the line and the highlight; the type is always the style card's two faces, and a font
they name that the card does not set is told to them in draft's output for your reply; its numbering
("1/4") numbers the cards. With no look, the colors are read from their photographs: a light ground when their median
lightness is high, else a dark one, both tinted with the photographs' dominant hue, which is also the line's. Every
photograph is graded once toward the set's median lightness before it is measured, framed or staged.

The reel is one camera over one wall, its beats:

| beat | the move reveals | it carries across the cut |
|---|---|---|
| moment-N, one per moment, each shown once: moment-1 the peak (the first moment by date when there is no peak), from the film's first frame, then the others in date order | the moment's photograph flying onto the wall on a band of the frame in its own color, the line acting on it its own way (climbing from the foot of its post's cell to the top, falling onto the top from the top of the frame, or riding in along the top, never the same act twice in a row), the day and place and the moment's line on the ground under the band, on a plate sized to them | the line, onto the next moment, as this photograph sets into its post's cell of the wall |
| closer | the camera pulling back to the wall of every one of the month's posts with a photograph and nothing else: each post's photograph in a cell with its day beneath it, the wall's grid fitted to how many there are (three posts make a wall of three, twenty a wall of twenty), the other posts rising out of the wall one after another, the moments standing out furthest, the line run out under the wall, "my september, in four stories" and the sign-off into next month; a post with no photograph has no cell, and a month with no photograph has no wall: the line runs out across the ground under the words | nothing: picture and sound stop together on the stop and hold still, the last hit ringing out and then more than a second of silence |

Each moment's beat is held for what its photograph carries: its words and how busy the photograph is, and the peak's
holds longest. One scale sets every hold so the reel fills the length asked; with none, it fills 15 s. Every sound is
a cue the board places where a beat lands (each moment's line landing above its subject, the moments standing
out of the wall, the stop), with the build into the peak and its impact, all mixed under the music; words rise and
the camera moves without a sound of their own. The board
lists the clips an image-to-video model would make, one per moment, and the move that stands in for each until one
arrives.

The cards are one a moment, in date order, numbered as a series. Each card is one camera over the moment's photograph
on the reel's system, with the same rule as the reel: no word stands on the photograph. The photograph fills a band of
the frame, from under the plates of the title and the sign-off to above the plate of the moment's words, the line is
ink drawn across it, and the words stand on the ground above and below the band, on a solid plate of the ground sized
to them. Each card's shots are cut to what its photograph carries: a busy photograph gets a longer look in and a
shorter hold, a quiet one the reverse, so no two photographs get the same cut.

| shot | the camera reveals | it carries |
|---|---|---|
| 1 | the photograph slides in, in its own color, and the line rises across it from its foot to above its subject; the first card carries the series' line, numbered as the look numbers it | the line |
| 2 | the camera moving in on the subject, framing its whole gesture, as the day and the moment's line land under the band | the subject |
| 3 | back out to the whole card, the line climbing on to the band's top | the line, standing above the subject |
| 4 | the held frame: the day and the place, the moment's line under it, and the handle signing off every card; the last card signs off into next month | nothing: the card ends on their words |

The handle and the month come from `month.json`; the handle is their username only, and with none there is no handle
line. Every close framing is worked out from the font files' own measures
of the type it holds, so the camera holds every line wholly in view or wholly out of it. When last month's
`build/template.json` exists (or `--template FILE` names one), it is the look and the board is marked `follows`, so the
series matches from month to month.

`storyboard.md` is the storyboard as the critic reads it: the reel beat by beat (its span in beats and frames, what
its move reveals, what it carries across the cut, every sound on it with the event it sounds on, and its clip), then
each card's idea, its shots with what each reveals, its sound cues and its words.

## Check and render the sheets

```
python3 S/scripts/storyboard.py check
python3 S/scripts/storyboard.py sheets
```

Run them as two commands, each on its own and with no `| tail` or other pipe after it, so you read each one's exit
code; `sheets` refuses a board that has not passed `check`, so fix what `check` fails before you run it.

`check` runs the board gates and writes `storyboards/check.json`:

- **structure**: three or four cards, each 15 s, every card's sound cues naming their event, and every line of type
  wholly in or out of view wherever a card's camera holds, inside the safe area on a whole-frame hold and clear of
  every other line; the reel's beats run end to end, every sound cue sits on a beat and names its event, and the last
  cue is the stop;
- **swap**: every card and the reel change when their moments do (the captions and the photographs moved between
  the moments), and every moment's move changes when the photographs move between moments: a frame another person's
  month would sit in unchanged is a template;
- **monotony**: the cards' timed cut has contrast (at least three shot lengths, no run of more than five equal shots,
  the longest shot at least twice the shortest, a held shot in every card);
- **words**: every word on the cards and in the reel lowercase, with no '!';
- **look**: with a look given, the board's colors are its palette's, every card's title opens with its numbering and
  every line is set in its font (or the family named in its place); with none, the colors are the ones read from the
  photographs;
- **counts**: their numbers on screen only when asked, and then every count counts up over its hold;
- **styles**: no two boards' looks share more than two of their six axes, every line is in one of its card's two
  faces, and every move and cut is one its card allows, chosen by what the beat holds.

`sheets` renders every reel beat once its move has landed (`reel-sheet.png`) and every card shot at its rest frames
(`sheet.png`) through `S/motion/studio` for each board, then `out/boards.png`: each look's hook, a middle beat and its
closer, numbered 1 to 3 with the look's name and one plain sentence about it, the page shown to the person in
movement 3. It writes `storyboards/sheets.json` with the findings: a font
(`FONT_ERROR`) or a photograph (`IMAGE_ERROR`) that did not load. The gate reads both again.

## Look at the sheets

Open each board's `reel-sheet.png` and `sheet.png` and `out/boards.png` with the Read tool, then any still full size
(`storyboards/<style>/reel/`, `storyboards/<style>/rest/`). In every reel beat and every card shot the photograph owns the frame and the line is ink drawn on it, never
the stage: a beat where a field of color fills the frame, or where the subject is cropped away, has its cause in the
board builder or the photographs; say so in the ballot.

## Done when

`check.json` and `sheets.json` are green and you have looked at every sheet and at `out/boards.png`.
