# 1. Research: find the trip, then learn how they travel

Goal: `trip.json`, `taste.md` (one page, in prose) and `taste.json` in the run's folder (`<run>/`), written
before any storyboard. Everything downstream reads taste first. The questions this kit's research answers: which trip, its
days and places in order, who was on it, the clips they shot, and how their travel posts look and sound against
their everyday ones.

## Run the counting

```
python3 S/scripts/research.py [--place "lisbon"] [--from 2026-10-03 --to 2026-10-08] [--album "..."] [--folder DIR]
```

Pass exactly what the person named; their words win over anything inferred. With nothing named, the most recent
trip is used. It runs `trip.py` (home is where they post month after month; a trip is a run of days away from it,
found from geotags, from albums and folders that span a few days, and from caption words when nothing is
geotagged; stops are places within a few kilometers, named by the place field, else the word their captions use
for it), then `picks.py` and `palette.py`, and counts:

- **the trip**: dates, each day with its places and its line (its strongest caption), the places in route order
  with their coordinates, the people tagged on it, their own clips from it;
- **the moments**: what happened at each place of each day, read from the captions alone: where they were, who is
  in the line, and the line itself; `taste.json` `moments` is that list, and nothing in it is counted;
- **travel against everyday**: the trip's palette against their everyday palette (and the colors only the trip
  has), brightness, saturation, caption length, posts a day, how fast their travel reels cut against their others;
- **voice**: caption length, case, emoji, punctuation, hashtags, sample lines from the trip;
- **likes**: the colors and themes of what they like and save;
- **music**: the music brief for this film, `taste.json` `music`, drafted from the trip's themes, the pace of their
  reels and the texture. Correct it the way you correct `register` and `avoid`; it is what the music is made from.

  | key | what it is |
  |---|---|
  | `mood` | one of music.py's beds: `calm`, `drive`, `film` |
  | `tempo` | beats per minute |
  | `styles` | three to six genre and instrument words |
  | `avoid` | what the track must not carry, as words |

  Never an artist, a band or a song: a name is not a taste. A track named on a travel post stays in `research.json`
  `music`.

Output: `trip.json`, `research.json`, a machine draft of `taste.json`, and
`taste.draft.md` (the numbers under the five headings). Read `trip.json` `assumptions`: if the trip it chose
is not the one the person meant, run research.py again with what they named.

## Read it like a creative director, then write taste.md

Open `taste.draft.md` and look at a dozen of the trip's photos (`photos/`) and a few everyday ones.
Then write `taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are on this trip: where they went, day by day, with whom, and what happened at each stop
  in their own line (`moments`); correct the list where a caption says it better.
- **You like** what their likes and saves have in common (palettes, subjects, pacing), with the accounts.
- **Your style is** how they travel on camera: the trip's colors against their everyday ones, light, texture,
  pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines from the trip.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their places, their people, their days and their words. American spelling.

## Fix taste.json where the reading says otherwise

`taste.json` is a draft: correct anything your reading contradicts (`pacing`, `texture`, `avoid`, `pillars`, each
day's `line`, the trip's `name`, and `names` for how a place is set on screen). Keep
every place and every person the trip has; never add one it does not. Keep its keys; storyboard.py, grade.py and
the critics read them.

## A caption that contradicts its photograph

The film sets each stop's caption over its photograph, so a caption that says what the photograph does not show
(a crowd over an empty lane, a sunset over a grey noon) is a contradiction on screen. When their own caption does,
keep it: it is theirs. When the material is a fixture or a seed that the kit or you laid out, fix it at its cause:
write each caption from its photograph (what the frame shows, in their voice) in the file that lays the fixture
out, and lay it out again. The trips in `S/evals/fixtures/` are written that way.

## Done when

`taste.md` has all five headings and `taste.json` matches it. storyboard.py refuses to run without
taste.md.
