# 2. The storyboards: the year with you, drawn from their moments in three looks

Goal: `B/storyboards/1/`, `2/` and `3/`, one per look, each with `storyboard.json`, `storyboard.md`, a sheet per
format (`sheet.png` 9:16, `sheet-feed.png` 1:1, `sheet-wide.png` 16:9: every rest moment) and `type.json` (what the
page could not load), and `out/boards.png`, the three looks side by side.

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` plans three boards with the board builder (`S/scripts/compose.py`) from what research found, one per look, each
the kit's one story, "the year with you" (`S/scripts/wall.py`), in that look's style card (`S/styles/<style>.json`):
board 1 scrapbook, board 2 analog-home-movie, board 3 editorial-quiet, or, when taste.json names a `style`, that style
first and the two of those three that differ most from it. It turns each card's palette rule and the photographs' own
colors into that board's grade (`B/grade.json`, `S/design/grade.md`) and grades the photographs into `B/public/graded/`.
Every face, color, texture, move and cut on a board is the card's; the tempo and the voices of its music are the
card's recipe, turned by the music brief.

- **the hook**: a photograph that shows the named one fills the frame in the look's photo layout: the one taste.json
  `hook` names (below), else the occasion post's when it shows them, else the latest one before the day that shows them
  most surely (a post that tags them or their own, then a caption that names them). The age the person gave lands
  inside the first second as one lockup: the figure at full size, and beside it at its right "<name> turns" over the
  day, when the person or their captions gave one (with no day given, no line states one). Nothing sits above the
  figure. On an anniversary the figure is the years the person gave; with no age or years given, and on a farewell, a
  graduation, a retirement or a tribute, it is the name, and the small line names the occasion ("dani · birthday",
  "dani · farewell"); a caption that states an age the person did not give stays off the screen. The occasion is the
  one the person named (`research.py --occasion`).
- **one card per moment** (taste.json `moments`, 8 to 15 of them, in the order they happened): each photograph lands
  in the card's photo layout (a taped print, a frame of home movie, a print in a wide margin) with the moment's name
  in its caption's own words, and under it the rest of the caption or, where the two commented under the post, their
  comments there, each in its writer's face, in the film's lowercase. Each beat moves by one of the card's moves and
  enters by one of its cuts, each chosen from what the beat holds (people or a view, words or none, the peak or the run
  before it), never by its place in the list, and every move leans before it goes and lands a little past before it
  settles. Each card holds as long as its photograph asks: 1.6 s to take it in, 0.3 s for each other person in it (up
  to three), 0.4 s when it tags them or is their own post, and its name and words at three words a second; the peak of
  the year holds longest, a quarter longer than any other, and the three cards just before it run fast, 1.3 s each
  with their names alone, so the peak lands after a run. The film runs the length the person asked for (else those
  holds added up, inside 20–60 s): the hook and the closer keep their beats, the run takes its 1.3 s a card, and the
  other cards share the rest, each at least 2 s and the remainder in proportion to their holds, so no grid of beats
  sets a cut. The last card before the closer shows the named one: when the last moment's photograph does not, the
  latest one that does moves there.
- **the closer**: the camera pulls back onto the wall of the year, a sheet of the look's ground carrying the wall's
  photographs falls shut over it with the age cut out of it in giant figures, and on the last hit the age's last figure
  punches through; then the card's closer takes the frame with the wish (the person's own line, `--line`, when they
  gave one) and its sender, and the picture and the sound stop together. The wall holds exactly the year's
  photographs: the square root of their count in rows, rounded, each row's cells filling the frame's width inside a
  margin (five photographs are a row of two over a row of three), so no cell is empty and every photograph is whole in
  the frame at the end.

The wall is what is carried across every cut: each moment's photograph leaves the frame for its own cell, and the
closer is the whole year of the two of them. Type that stands on a photograph is the card's light color over light
taken out of the picture under it, or its ink where the picture is bright, so it reads on the photograph itself; type
on the card's paper or ground is the card's ink.

Every word on the board is one the two wrote (a caption, a line they traded) or the closer's wish, name, number, date and sender; every
photograph is one they share. The film's captions are the posts' own text, so a caption that contradicts its
photograph is fixed in the post, never in the film. A post is shown with its own photograph and never with one found
by its words or its date: a post with no photograph of its own is not shown, and a video contributes nothing. The
board is one plan for every format: its length in seconds (`length`, and where it came from in `length_from`), and
each beat a form (hook, moment, closer), the post, the moment's name and the words it carries, and on a card its
`hold`, the seconds its photograph asks for. The builder lays each card out for 1080×1920, 1080×1080 and 1920×1080,
each solved for its own frame (the edge, the photograph's size and the type's side), never one frame scaled into
another.

A thin year is planned with what there is: fewer moments make fewer cards and a wall of fewer cells, one per photograph; a friend with
no posts of their own gets the person's posts of the two; nothing is invented to fill the gap. A thin year's cards
share the same length, so each holds longer: never raise the bpm or a card's hold by hand to change the length. A
year with more moments than the length holds at 2 s a card keeps the ones spread across it, those that show the
named one first.

`storyboard.md` says per beat what the move reveals and what it carries across the cut; the music's origin, the music
brief, and the `mixed:` line `music.py master` fills with the bed's and the effects' loudness; and the sound cues, one
where each beat lands (a hit as the hook lands with its age and as each moment's card lands with its name, the build as
the sheet falls over the wall, its impact, a hit as the last figure punches home, the stop on the wish; words rise and
the camera moves without a sound of their own).

## Choose the hook

The hook is the first thing anyone sees: one photograph of the named one, sharp, the face clear and the light
good. Open the hook's photograph on the 9:16 sheet. When another shared photograph of them would stop a thumb better
(a clear face over a back turned, daylight over a dark room, the two of them over a crowd), name it in `B/taste.json`
as `"hook": "post:N"` (`"post:N#K"` for a carousel's K-th photograph), the ids `B/shared.json` lists under `items`, and run
`draft` again. A name that is not a shared still photograph is refused, saying which to name.

## Record what each photograph is of

The builder places the edge by the photograph's lines and cannot know what the photograph shows, so every photograph
the board places carries its subject box, written by you after you look at it. Open each photograph the board's
`photos` names (`B/photos/<file name>`) with the Read tool and add to its entry in `storyboard.json`:

```
"subject": [x0, y0, x1, y1]
```

the box that must stay whole off the type's side of the edge, in fractions of the photograph's width and height from
its top left. The box is the part of the photograph the card is about, as its caption says it, and as tight as a
careful person would draw it:

- a person or people: them and what they hold (the surfer and the board, the two on the bench, the hands and the bowl)
- a view: what the caption is about (the roofs and the river of a city view, the ridge of a mountain morning)
- a still life or a room: the thing itself (the cup and its art, the candles on the cake, the banner and the balloons)

The whole print, `[0, 0, 1, 1]`, is never the default. Record it only where the whole print is what the card is about,
and say which photograph and why when you report the board. The photograph always covers the frame; the edge and the
type take the side of the subject with room, and where a subject is taller than the frame can hold (a portrait
photograph in the wide frame) its top part stays in frame. A redraft keeps each photograph's box; `check` names every
photograph that has none.

## Write each clip's shot

`storyboard.md` lists under `## clips` the clips an image-to-video model would make for this board: the hook's world,
texture between chapters and a still brought to life, each on its beat. The board measures each one's lens feel,
camera height, light, the part of the photograph its card shows and its length from its photograph; what the
photograph shows and what in it would move are yours.
Open each clip's photograph with the Read tool and write on its beat in `storyboard.json`:

```
"shot": {"subject": "what the photograph shows, in your words", "moves": "what in it would move in the clip"}
```

for example `{"subject": "a surfer standing at the sea's edge at sunset, the board under one arm", "moves": "the surf
running in around the ankles and back out, the low sun glinting on the wet sand, hair lifting in the wind"}`: the
people, the place and the light as a cinematographer would name them, never the caption pasted in. The film loops
the clip, so every motion you name comes back to where it started within the beat (surf running in and out, grass,
hair or a flag in the wind, steam, a flame, light glinting on water, a slow breath); never a motion that crosses the
frame, arrives or changes for good (a bird flying across, a head coming to rest on a shoulder, the light dimming). `check` names every clip with no shot; a redraft
keeps each photograph's shot.

## Check, then look

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` lays the board out in all three formats and refuses, in plain sentences: a film outside 20–60 s, or more than
1 s off the board's length; a line
outside the format's safe area as the camera shows it at rest, or drawn under 28 px cap height (figure height for
numerals) at 1:1; a line on the subject's side of its card's edge; an edge that leaves more than half of the subject
on the type's side, or a frame that shows less than 40% of it; the giant age past the frame's margin; a photograph
with no subject box; a clip with no shot; a line that is not one the two wrote; a photograph that is not one they share; the hook's event
after frame 30. A photograph whose post has no caption is a wordless card, its name and words empty and only the
lines the two traded under it, if any, on its edge; `check` passes it as it is.

`sheets` renders every board's rest moments (the hook, the middle card, the closer) through the studio composition at
quarter size in all three formats, and lays the three looks side by side in `out/boards.png`, the sheet the person
chooses from; a font or photograph the page could not load is a refusal there too.

Open each board's three sheets with the Read tool, then any frame that looks wrong full size. A hook that would not stop a
thumb, a face cut by the edge, type that fights its photograph, a card that could be any other card: name another
hook, change that board's photographs, their boxes or their order in its `storyboard.json` (a photograph is any shared one
named in `B/picks.json`) and run `check` and `sheets` again.

## Done when

Three boards whose `check` is clean and whose sheets are clearly the two of them, every card its own photograph,
each plainly its own look, and `out/boards.png` drawn from them.
