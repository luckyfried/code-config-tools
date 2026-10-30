# 1. Research: learn who they are before making anything

Goal: the run's `taste.md` (one page, in prose) and `taste.json`, written before any storyboard. Everything
downstream reads taste first. The two questions this kit's research answers: which nine are theirs by their own
numbers, and what moment each of the nine was.

## Run the counting

```
python3 S/scripts/research.py --run build/<stamp>
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts: the year's palette and the palette of what they like
and save, caption statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph
(who gets their likes and what those accounts share), cadence, how long their reels run and how fast they cut,
their people and places, then the two this kit needs most: **the nine** (their nine top posts and reels of the
year by the numbers the data carries: likes, then comments, then saves, then the newer post; the nine most recent
when the data carries none of the three, which `stats.py` prints and the brief records; for each, its subject, its two
strongest colors and what its caption says) and **the moments** (the nine in the film's order, the ninth first and the
first last, each as its day, their caption line, the people they tagged and the place they named). `picks.py` also
finds each photograph's focus point, its square crop, which every storyboard places it by, and its look (a small
fingerprint of the picture, which tells the storyboard when one photograph repeats another).

A year with fewer than nine posts and reels makes nothing: `research.py` prints `not delivered: <n> posts, nine
needed` and exits 4. Tell the person that sentence and stop. Output, in the run: `research.json`, `picks.json`,
`palette.json` (the year's colors and the roles the film is set in: its accent is the most vivid color of their
photographs, weighed by how much of the year it covers, its paper the palette's warm white), a machine draft of
`taste.json`, and `taste.draft.md` (the numbers under the five headings).

## Read it like a creative director, then write taste.md

Open `taste.draft.md` and look at a dozen of their photos (the run's `library/posts/`, or the photo folder named in
`library.json`) and the liked media if the library has it. Then write the run's `taste.md` yourself, one page, five
paragraphs that start exactly:

- **You are** who they are this year: what they post, where the year went, and the nine as the moments they were,
  from the ninth to the first: what happened, with whom and where, in a sentence each from the photograph and their
  caption, and what the nine share that the rest of the year does not.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors (the year's and where their likes pull them), light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their photographs, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

The run's `taste.json` is a draft. Correct it where your reading says otherwise, and keep its keys; the storyboards,
the critics and deliver.py read them.

| key | what it holds |
|---|---|
| `seconds` | the length they asked for ("a 20 second reel" is 20; "under a minute" is not a length and leaves it `null`); `null` makes the reel 30 s. The reel runs 20 to 45 s; a length outside that makes nothing, and the storyboard says so in one sentence to pass on |
| `style` | a look they named ("swiss", "scrapbook", "like a film"): one of the style ids in `S/styles/`, and the sheet shows it with the two looks that differ most from it; `null` shows the kit's three |
| `ask` | `true` when you may ask them which look; `false` when nothing may be asked (they said not to ask, or the session runs unattended), and the look is picked by taste |
| `words` | the title, the promise and the ask the film sets on screen, in their voice: their case, their length, their punctuation |
| `register`, `nine[].why`, `avoid` | how they write, why each of the nine is theirs, and what would be wrong for them |
| `moments` | what each of the nine was (the day, their line, who, where), joined to its post by `ts`. Each `line` is what the film sets on screen for that post: cut it to the words they would say out loud about the day, in their case. A caption whose only words are an account figure ("1,000 followers") gets `line` "", and that moment is wordless but for its day |
| `order` | the nine's `ts` from the first to the ninth, as their numbers rank them; never change it |
| `music` | the brief the film's bed is made from when they gave no track: `tempo` (beats per minute, 100 to 140, or `null` for the story's own), `styles` (genre and instrument words that fit them; empty leaves the look's own sound) and `avoid` (what the music should never have, each a noun: "vocals", "big drops"). Never an artist, a band or a song |
| `beats` | empty; the one fix after the critics writes a beat's `layout`, `move` or `seconds` here |

Never change which nine they are: that is their numbers, in the run's `stats.json`.

## Done when

`taste.md` has all five headings and `taste.json` matches it. storyboard.py refuses to run without taste.md.
