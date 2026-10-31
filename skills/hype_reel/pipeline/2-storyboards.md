# 2. Storyboards: three looks of the hype reel, made of this subject and this person

Goal: `storyboards/1/`, `storyboards/2/` and `storyboards/3/`, one per look, each with `storyboard.json` (the film the
studio composition renders), `storyboard.md` (the same film in words: its idea, its beats, its cast and the rule
behind each part), every beat at rest (`frames/NN-<beat>.png`), the feed post (`frames/feed.png`) and `sheet.png`;
`out/boards.png`, the three looks side by side; `storyboard.py check` clean.

## Look at the feed first

```
python3 S/scripts/cast.py looks
```

It reads what each feed photograph shows from its words (people, a pair, a gathering, a place they named, night, a
low sun) and guesses where its subject sits. Open `looks.png` with the Read tool: every
photograph is numbered with a red box on its subject. Where a box is not the subject (the subject, the people), set that
entry's `subject` in `looks.json` to `[left, top, right, bottom]` in fractions of the photograph; set `checked` to
true on every photograph you looked at; set `skip` to true on a photograph that should play no part (not theirs,
not their kind of thing). Every frame keeps a cast photograph's subject whole, so the boxes decide the crops.

## Draft

```
python3 S/scripts/storyboard.py draft
python3 S/scripts/cast.py show
```

`draft` casts the film from the feed and the subject (each part's rule is in `cast.py --help`), grades each cast
photograph into `public/photos/<part>.jpg`, stages the subject's stills and footage as they are, and lays the one story
out three times, once per look. The looks are the style the person named (`taste.json` `style`) and the two of the
kit's three that differ most from it, or the three when they named none:

| look | what it is |
|---|---|
| kinetic-type | their words slammed big and bold on flat color, cut hard to a fast beat |
| cinematic-letterbox | their photographs between black bars, with slow dissolves and quiet subtitles, scored like a trailer |
| swiss-grid | clean white pages with their photographs set in a grid and crisp type, cut to a steady pulse |

The story is the same in all three, and it is the plan in `taste.json` `plan`: the hook (the first two seconds, the
plan's hook line over the subject's strongest picture, or over their latest photograph of making it when the subject is
theirs), the build (the subject's own pictures and footage and the person's photographs around it, each with its own
words on it, a fact or a line of theirs, or none), the reveal of the subject under its name (set as a title, at the
size the look gives one), and the closer with the
name and the plan's punchline, or the date for a launch. The subject is on screen for at least half the film before
the closer. Each beat holds as long as its words take to read, 0.6 s to settle and about 0.3 s a word (counted from
the landing, on a move that flies its photograph in, which holds its flight even with no words), and the reveal holds
longest, so no two films run the same rhythm.

The plan's tone sets the pace and the number of build beats, the case of the words and the cuts each look prefers:

| tone | what it plays like |
|---|---|
| default | playful and clean, hard cuts and slides |
| polished | restrained, longer holds, slow fades between pictures |
| yc-parody | a deadpan startup launch, played completely straight, hard cuts |
| chaotic | fast and loud, all capitals, flash cuts, the most beats |
| deadpan | calm, big empty space, the fewest beats, hard cuts |
| cinematic | trailer scale, big capitals, bars closing and long dissolves |
| app-store | clean feature cards, one claim each, slides and wipes |

Each look takes everything else from its style card (`S/styles/<style>.json`): the faces, the colors (the card's
palette rule over the swatches of both palettes), the tempo, the finish and the closer, and each beat's move and cut
from the card's allowlists, chosen from what the beat holds: a beat with no words takes no move that sets words while
the card has another, a beat with words takes no move whose words leave as it opens, the reveal's move is its own (no
other beat makes it while the card has another), a beat that shows the subject after the hook takes no move that
covers it, the film never opens on black or on a title that only fades up, a move that sets two words at most takes
only a beat whose whole line is that short, a move that counts takes only a beat whose own words hold a number, a cut
never takes more than three eighths of either beat it joins, and two beats that both carry words never crossfade while
the card has a cut that jumps (the words stagger, or the picture dips through the ground). The looks reach for the
shared photo moves where they fit: slam-words and counter on kinetic-type, picture-tunnel on cinematic-letterbox,
exploded-layers on swiss-grid's reveal, and tilted-wall on a swiss-grid photograph of the build with no words, which
stands as one of the set.

Per beat the board says the moment it shows, their photograph of it (its day) and their words on screen
(`storyboard.md`). The photograph owns the frame at every beat, the way the look sets it: sharp and covering the
frame, or set on the look's page; never a blurred, washed or frosted copy of the photograph behind the type. The
reveal's name stands off the photograph where the look gives it a place: on the grid's page in the line cell the
grid sets apart from the photograph, in the letterbox's lower matte under the picture. Words slammed in one a beat are set by the kit at one size,
the size their longest word takes to land whole in the frame.

**The hook line and its picture are one entry** (`hook` in the board): `plan.hook` over the subject's strongest
picture, or their latest line about making it over that photograph; `said.hook` replaces the line. Nothing is chosen
by likes, comments or saves, and no number is on screen but the ones in the subject's own words, the person's, and the
date. With a single picture of the subject the hook frames it close and detail beats frame closer parts of it in turn.
For a launch the date on the closer is set as they wrote it: "14 November" when they lead with the day, "November 14"
when they lead with the month. `show` prints the cast with the rule behind each part.

## Check, render the sheets, look

```
python3 S/scripts/storyboard.py check
python3 S/scripts/storyboard.py sheets
```

`check` holds each board to its style card (faces, colors, moves and cuts from the card; the three looks apart from
each other; no single shot length, no one place for the words, no move on two beats running), the safe area, the
subject's own assets, the date on the closer for a launch, the subject's share of the film and a length of 15 to
25 s. It names
each finding with its board and beat. Where they asked for a length the film cannot run, `draft` prints one line under
the boards saying the length it made and why.

`sheets` renders every beat at rest and the feed post through the studio composition, the same one the film is
rendered with, and lays `out/boards.png`: for each look its hook, a middle beat and its closer at half size, with its
name and one sentence. Open each `storyboards/N/sheet.png` and `out/boards.png` with the Read tool, then any frame that
looks wrong full size. While
`check` finds anything on a board, `sheets` renders nothing and exits with one line per finding
(`storyboards/N/storyboard.json is not rendered: <the finding>`): fix the board first.

What to fix, and where: a subject box (`looks.json`, then `draft` again), a photograph that should not play
(`skip`, then `draft`), a line that is wrong for its photograph (`taste.json` `moments[].line` for that photograph, from
their own words, then `draft`; the hook line can also be led by `taste.json` `said.hook`), an item that collides (its place in `storyboard.json`). Run
`check` and `sheets` again after every fix.

## Done when

Three sheets that each look like a hype reel clearly about the subject and clearly in the person's voice, `out/boards.png`, and `check`
prints no finding.
