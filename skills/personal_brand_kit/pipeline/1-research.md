# 1. Research: here the research is the product

Goal: `taste.md` (one page, in prose), `taste.json`, `brand.json` and `out/plan.md` in the run folder, written
before any storyboard. The film and the plan read these. Every finding carries a number and an example
from their own feed; nothing is guessed.

## Run the measuring

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then measures (see `research.py --help` for each): the palette
(the named colors their posts lead with and the share of posts each leads), the compositions they repeat, the
caption devices (each with its share and three real captions), the pillars (subjects clustered from their
captions, shares summing to 1), the cadence (weekdays and times), what their likes aspire to (palette and
subjects of the liked images and accounts, against their own), the posts that fall outside their system, and
their moments (every captioned post as what happened: its date, its caption's own line, the place it names, the
people it tags, its pillar, its photograph). Output: `research.json`, a draft of `taste.json` with the brand draft
under `brand`, and `taste.draft.md` (every finding under the five headings).

## Read it like a brand strategist, then write taste.md

Open `taste.draft.md`, look at a dozen of their photos (`photos/`) and the liked images if there are any. Then
write `taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** what they post and how much of each (the pillars with their shares), the moments that show who they
  are (what they did, made or went to, where, and with whom, in their own lines), and the one line that says it.
- **You like** what their likes and saves have in common (palette, subjects), with the accounts, and how far that
  is from their own feed.
- **Your style is** their palette by name and share, the compositions they repeat, light, texture.
- **Your voice is** how they write: case, length, emoji, the devices they lean on, three of their own lines quoted.
- **Avoid** what breaks the system: the posts outside it (say kindly what they do and how they landed), and
  anything the data says is wrong for them.

What the person said about themselves (their bio, the request) wins over inference: their own words go in first.
Use their numbers, their account names and their words. American spelling.

## Fix taste.json, then build the system

`taste.json` is a draft. Never change a measured share or hex. Correct what your reading contradicts, then set:

| key | what it holds |
|---|---|
| `ask` | `true` (the default): show the three looks and ask which. `false` when they said "just make it" or there is no one to ask; you then pick by their taste and say why in one line |
| `style` | a look they named in their own words, as a style id from `S/styles/catalog.md` ("make it like a scrapbook" is `scrapbook`); it leads the three looks. `null` for the three defaults: kinetic-type, editorial-quiet, swiss-grid |
| `hook` | the film's opening line in their words, when they gave one; `null` takes the first phrase of their bio |
| `question` | the question the film asks the viewer, in their words; `null` takes the question from their best-liked caption that asks one |
| `signoff` | the last words on screen; `null` takes their name |
| `music` | `words`: the instruments or feel they asked for ("soft piano", "strings"), which choose the bed's recipe; `avoid`: what the music must never have, each a noun ("drums", "vocals"). Never an artist, a band or a song: a name is not a taste |
| `avoid` | the habits the brand keeps clear of, in plain words |

Then edit the `brand` block in their words: the statement (one line), the color names (plain names a person would
say: "terracotta", never a hex), pillar names, the voice lines, the stop list said kindly, the aspire line.

Then curate `moments`, the film's story, in the order the film should play them: keep the real moments (a thing they
did, made, went to or pulled off, a person they did it with) and drop the posts whose caption only describes the
picture; cut each `line` down to their own words, short enough to stand whole over its photograph, never add to it;
leave `line` empty where their only words are a figure about their account ("1000 followers"), and that moment plays
without words; keep each moment's `pillar` (it is the moment's label on screen) and its `photo` by path. Put the
moment that matters most last: the film builds to it. Once you have curated them, change `written_by` to say so (for
example "the agent, from taste.md"): while it still says `research.py draft`, the story is drafted for you, each
pillar's best-liked moment in the order of the pillars' shares, the best liked last. Six moments play at most, and a
look with a slow pace plays fewer (the film stays within 12 to 30 s, the least liked left out first, the last always
kept).

```
python3 S/scripts/brand.py system
python3 S/scripts/brand.py plan
```

`system` writes `brand.json`, validated against `S/design/brand.schema.json` (palette roles, pillar shares
summing to 1 within 0.01). `plan` writes `plan.json`: 30 days from tomorrow, a feed post on each cadence day
at its time and a story on the others, the pillars dealt in their proportions, every caption a draft marked
`"draft"` and built from their own pieces. Rewrite every caption in `plan.json` in their voice (their case,
their length, their devices, their hashtags), then run `brand.py plan` again: it renders `out/plan.md` and puts
the first seven days into `brand.json` as `first_week`.

## Done when

`taste.md` has all five headings, `brand.json` validates, and `out/plan.md` has 30 dated entries in
their voice. `storyboard.py draft` refuses to run without `brand.json`.
