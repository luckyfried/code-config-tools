# 1. Research and cast: learn who their people are, then cast their photographs

Goal: `R/taste.md` (one page, in prose) and `R/taste.json`, then `R/cast.json` and `R/public/matched/`: each
person's photographs, where in each the person is, all of them matched to one light. Nothing is drafted before
these exist. The two questions this movement answers: who their people are, by their own words or by every signal
counted together, and which of their photographs carry each of them.

## Find their people

```
python3 S/scripts/research.py [--people a,b,c] [--top N]
```

`--people` when the request names people, as handles in the order they named them (when they used first names,
run `research.py` once without it and take each one's handle from the ranked list in `R/people.json`). `--top N`
when they asked for a number of people. Neither: the five people every signal together puts first. A `R/people.txt` (one handle per line)
works the same as `--people`. An account with fewer than five people in its photographs makes a film of the people
it has.

It runs `people.py`, `picks.py` and `palette.py` first, then reads the year: palette, captions, likes, cadence,
reels, places, and the two this kit needs most:

- **the people**: who they are and why each is there, in plain words (in whose photographs, who comments under
  whose), each person's stretch of the year (the months they lead), their moment (the photograph of the two of
  them, its month and place, the person's caption of it), their best line and where it came from, their other
  lines, their voice, the exchanges between them and the person, and who came next;
- **the photos**: each person's best photograph, the group photographs, and the one with the most of them in it.

Output: `R/people.json`, `R/picks.json`, `R/photos/`, `R/research.json`, a machine draft of `R/taste.json`, and
`R/taste.draft.md` (the draft under the five headings).

## Read it like a creative director, then write taste.md

Open `R/taste.draft.md` and look at each person's photograph and a dozen of the group photographs (`R/photos/`).
Then write `R/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are this year and who they spent it with: each person in a sentence (what the two of them
  did, where and when, the photograph, the line), and how the year moved from one of them to the next.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors, light, texture and pacing.
- **Your voice is** how they write, and how each of their people writes: case, length, emoji, punctuation, two or
  three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their places, their account names and their words. American spelling.

`R/taste.json` is a draft: correct what your reading contradicts (`register`, `pillars`, `avoid`, `places`).
Each person's `line` is the words their card says for their moment: keep it, or swap it for the one of their
`other_lines` (in `R/research.json`) that says most about what the two of them did, and a caption whose only words
are a number about posting or followers leaves the line empty. The card says a line without its emoji. Never change who the people are: that
is their own list or what every signal together found. Their order in `R/taste.json` is the film's: the draft lists
them as their own list gave them, else by the month of their moment; put them in the order the story runs, and the
last one closes the film, holds a beat longer and stands across the foot of the wall. Never write a line for anyone. Keep its keys; the
storyboards, the caption and the brief read them.

`music` is the brief that steers the bed `music.py find` composes in the picked look's own recipe when the person gave
no track; correct it the way you correct `register`, from what you read about them and from the film's theme (the
people who made their year, one by one, closing on the wall of all of them):

| key | what it holds |
|---|---|
| `mood` | the feel in a word, `calm`, `drive` or `film`: how they would describe it |
| `tempo` | beats per minute, only when their own reels set one; leave it out and the recipe takes the middle of its own range |
| `styles` | genre and instrument words only when they point away from the look's own recipe (a recipe's id or its words); an export's music attribution gives genre words only |
| `avoid` | what the music should never have, each written as a noun ("vocals", "big drops") |

Never an artist, a band or a song: a name is not a taste.

## Cast the photographs

```
python3 S/scripts/cast.py draft
```

`R/cast.json` starts each person from their best photograph and more of them, alone first (three each for three
people or more, four each for two, nine for one), and the group from the photograph with the most of them in it.
Open every photograph it names with the Read tool and correct, for each, `point` (what a crop keeps in view: the
face, or the person when no face shows), `face` (the box a crop at rest must show whole: brow to chin and ear to ear, never the hair or a hat above it; leave it out for a back, a
silhouette or hands), `tip` (where their tag points: on the person, never on a thing beside them; the tag stands under it, so on a figure small in the photograph, a surfer on the shoreline, the tip goes at their feet and the tag stands on the ground below them) and, for the group photograph, `heads`
(a head only where you can see that it is that person; a crowd's backs or strangers get none, and the hook then opens
on the photograph with every person's tag in a row under the title). For the group photograph
and each person's first one, write `shot`: the clip a cinematographer would make of it, in one sentence of your own
from what you see (who or what moves in it, and how); the lens, the height, the light, the camera's own small move,
the length and the loop are measured and added to it. Swap a photograph that
does not show the person, shows them too small to read as a person, or carries someone else's mark (a photographer's
watermark) for another of theirs from `R/photos/`, and when none other shows them, set `trim` to the part of it
that leaves the mark out (its corners as fractions of the whole photograph; every point stays a place on the whole);
set `keep_light` on one whose light is the point (a
sunset silhouette, a night lit by a fire). `cast.py --help` has every key. Then:

```
python3 S/scripts/cast.py match
```

`match` moves every cast photograph most of the way to the set's black and white points and its colorfulness, and
its color cast toward the warmth of the year's palette, under one film curve, so every photograph reads in one grade, and writes them with the fonts and the grain into `R/public/`, the folder the renderer serves. A photograph as
wide as it is tall or wider is kept whole, and the film mounts it the way the look's card says (taped to the page,
projected on the dark, or laid flat on a field of the card's color), never over a blurred copy of itself; its points,
faces and heads stay as you set them on the photograph.

## Done when

`R/taste.md` has all five headings, `R/taste.json` matches it, and `R/public/matched/` holds every person's
photographs. storyboard.py refuses to run without taste.md.
