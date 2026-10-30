# 1. Research: learn where they went and who they are before making anything

Goal: `places.json` (every place of the year, in order, with coordinates), `cast.json` (the photographs each visit
shows), `taste.md` (one page, in prose) and `taste.json`, all in the run's folder and written before any storyboard. Everything downstream reads them. The two questions
this kit's research answers: where did they go and what did they do there, in what order, and what does their travel
look like against their everyday.

## Run the counting

```
python3 S/scripts/research.py [--set DIR]
```

`--set DIR` names a set of photographs of the year's places the person handed over: a folder per place, named by the
place, each ranked best first by a `manifest.json` beside the files (`{items: [{rank, file, description}]}`) or, without
one, by file name. The set is read as files, never run or changed; with it, the film's photographs come from the set.

It runs `places.py`, `stats.py`, `picks.py` and `palette.py`, then counts. **The places** (`places.py --help` has
the rules): geotags first, then the places named in captions, albums, folder names and check-ins, merged into one
list in visit order, each with its coordinates, date span, visits, posts, stories and photos, and where it came
from; the route between them; home; the region the map is drawn at and
the far trips; the places named once and left off (`mentioned`); and the rows that name no place (`unplaced`).
**The palettes**: the travel palette (photos away from home) against the everyday palette (photos at home) and how
far apart they read, with the palette of what they like and save. Then caption statistics (length, case, emoji,
punctuation, hashtags, the words they use about each place), the like-graph, cadence, how long their reels run and
how fast they cut, their people, and the moments: one per visit of the route, drafted as the visit's first post (its
caption, the people tagged in it, its photograph), with every caption of the visit after it in time order as the
candidates. Output: `research.json`, a machine draft of `taste.json`, `taste.draft.md` (the numbers under the five
headings), `places.json`, `picks.json` (each place's best photos and reels, and each visit's moment), and `cast.json` with its contact sheet
`cast.png`.

## Look at the cast and correct it

`cast.json` lists the visits in route order, each with the photographs it shows, the first the visit's own print: the
photograph of the visit's moment, set or no set, then the best the place has that an earlier visit has not shown, two
in all for a visit in the home region, three for a far place. `storyboard.py draft` always puts the moment's own
photograph first (the one its post carries, or the one `taste.json` pairs with it), so correct the other shots here and
change the moment's photograph in `taste.json`.
Open `cast.png` with the Read tool: every visit's shots beside the place's other photographs. Correct `cast.json` by eye
where a shot is wrong for the film: a photograph that does not say the place (an interior that could be anywhere, a
blurred frame), two shots of one subject, a second visit that repeats the first. Keep each visit's `place` and `n`;
change only its `shots`. A cast whose visits still match the route is kept as you set it on every later run.

Then give each visit's first shot its own line: the photograph's strongest straight line, read by eye on the
photograph (a horizon, a roofline, a rail, a waterline, the edge of a bar or a bridge), written as
`{"file": "...", "line": [u0, v0, u1, v1]}`, its two ends as fractions of the photograph from the left and from the
top. The film's cut runs at its slope, so a print without one gets the same level cut as every other and reads as a
template. The caption's strip stands in a band at the top of the frame, above the photograph, so no line has to be
chosen to keep it off the subject. `storyboard.py draft` marks each card's `own_line`; look at the hook and the stop
on the sheet to see that the cut runs the way you meant.

Write two more on that shot, read off the same photograph, the way a cinematographer names a shot: `about`, its
subject and light ("a fishing boat pulled up on a pebble beach in low evening sun"), and `camera`, its lens feel and
height ("a 28 mm lens at waist height, close to the hull"). `clips.py list` writes each stop's clip request from
them: what the shot shows, how the camera moves, and through which lens. Without them the request names only the
place and its line, which reads as a template. Write a third, `texture`, the place's material close up in its light with
no subject and no landmark in it ("limewash flaking off a sunlit wall", "river water sliding under a low sun"), which a
stop the trip leaps to or from asks for between chapters in place of the photograph's subject.

## Check the places against their own words

Open `places.json` and read its `assumptions`, `mentioned` and `unplaced`. Their own words win over inference:

- they say where home is (in the request or their bio): `places.py --home <place>`. Home measures the distances on the
  map; it is a place and a stop only when they posted from it;
- a place they went that has no geotag and is named once (`mentioned`): `places.py --add <place>` (or
  `--add "Name@lat,lon"` for a place the gazetteer lacks);
- a check-in or a file name the gazetteer lacks, on a row with no geotag (its line in `assumptions` names it):
  `places.py --add "Name@lat,lon"` at the place's coordinates, and the rows that name it become its photographs;
- a place they did not go (a caption that names a place they miss): `places.py --drop <place>`;
- a geotag that names the wrong town (a suburb for the city they mean): `places.py --rename "Suburb=City"`;
- a place shown under another spelling than theirs: `places.py --rename "Fez=Fes"` (the name as they write it).

Each correction is kept and replayed on every later run. Run `research.py` again after a correction so the picks
and the palettes follow the places.

## Read it like a creative director, then write taste.md

Open `taste.draft.md` and look at a dozen of their photos (`photos/`), some from away and some from home,
and the liked media if `library/` has it. Then write `taste.md` yourself, one page, five paragraphs
that start exactly:

- **You are** who they are this year: where the year went, place by place, and what they did at each (the moments:
  their line, the people with them, the photograph), what they photograph when they travel, and what they say about
  the places.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors (the travel palette against the everyday one, and where their likes pull them),
  light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, a map-tile look, whatever
  the data says).

Use their place names, their people and their words. American spelling.

## Fix taste.json where the reading says otherwise

`taste.json` is a draft: correct anything your reading contradicts. The film reads its `handle` and its `moments`; the caption reads
its `register` (case, length, emoji, hashtags) and `year`; the brief and the critics read the `palette`, `avoid` and
`pillars`. Never change the count or the places there: they come from `places.json`, which you change only through
`places.py`. Keep its keys.

`seconds` is the film's length when they asked for one (a number from 20 to 42), else `null`, and the film runs at its
own pace inside 20 to 42 s. Every stop's hold is scaled by one factor to that length. A length the places cannot make
(too short for every stop to be read, or too long for every stop to hold well) is made as near as they make it, and
`storyboard.py draft` names the length made beside the one asked; a trip too small to fill 20 s runs as long as its
photographs carry. Only places whose names alone, with every line left out, take longer than 42 s to read are refused,
in one line: drop places with `places.py`.

Two keys are optional and the draft leaves them out, so the kit's own values hold: `texture` (`grain` and
`vignette`, each 0 to 0.4) is the grain and the vignette over the whole film, and `closer` (`map`, 0.35 to 0.75) is
the map's share of the closer under its strip. The year's palette is the one grade every photograph and the paper
take. The critics reach for these as levers (`S/critic/critic.md`); set them here only when your reading of their
style says so.

`music` is the brief the film's music is made from when no track is placed: a `tempo` in bpm only when they name one
(else the picked look's), `styles` (genre and instrument words the picked look's recipe takes in) and what to `avoid`.
The picked look sets the music's recipe; their words only steer it. Correct the brief from their register, their
pacing and their places the way you correct `register`. A tempo they name stays from 90 to 110 bpm, where every place
holds its line and the film runs inside 42 s. Name a sound, never an artist, a band or a song: a name is not a taste.

`style` is the look they named, one of the kit's three looks or any other style card, else `null`; `ask` is `true`
unless they said to pick for them, and then the agent picks the look by research.json's `lean`, with its one-line
reason.

`moments` is the film's words: one row per visit of the route (`place`, `n`, `line`, `with`, `post`), in route order.
Read each visit's candidates in `research.json` (every caption of the visit with its post, in time order) and keep, as
its `line`, the one that tells what they did there, whole and in their words (two words are a line), with that
caption's key as `post`, or `null` when none of their captions from that visit says anything: that beat is wordless.
Never shorten a line to make the film fit: `storyboard.py draft` fits the lines to the film itself, setting the longest
line to its first clause (with none left, leaving out the longest line away from the hook and the peak) until every
stop can be read inside 42 s with the peak holding longest, and lists each one it set in `storyboard.md`. The line and its photograph are one post: the beat shows the post's own photograph
under its words, and a post with no photograph (a reel) leaves the beat wordless on the place's own print. A photograph
of the set stands for a moment only where you pair them, by writing its path as the row's `photo`. Never write a line
they did not post.

Mark the story's peak: `"peak": true` on the one visit that is the best moment of their year (the thing they would tell
first). It holds longest and is the stop the sheet shows; how far away a place is never decides it.

## Done when

`places.json` lists the places they went, `cast.json` is the cast you looked at, `taste.md` has all five headings
and `taste.json` matches it. storyboard.py refuses to run without taste.md.
