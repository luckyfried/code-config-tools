# 1. Research: who the film is for, and everything the two share

Goal: `B/taste.md` (one page, in prose) and `B/taste.json`, written before any storyboard. Everything
downstream reads taste first. The questions this kit's research answers: who exactly the film is for, what the
occasion is, which photos and videos the two share, what they say to each other and how, and how the friendship
changed over time.

## Find the named one and count

```
python3 S/scripts/research.py --who "<their words for who it is for>" [--occasion "<their words>"] [--date YYYY-MM-DD] [--words "<anything else they said about them>"] [--line "<their own line for the wish>"] [--seconds N]
```

`--seconds` is the length the person asked for, from 20 to 60; leave it out when they named none. A length outside
that range prints `not delivered: <n> s is outside the 20–60 s this kit makes, ...` and writes nothing: tell the person
that line and stop.

Pass the person's own words: a handle (`"@dani.reyes"`), a name (`"Dani"`, `"my mom, Ana"`), or `"us"` for an
anniversary. `research.py` runs three steps and then reads the result:

- `shared.py` finds the named one. An exact handle wins; a name is matched against tagged accounts, mentions,
  comment authors and feed names; "us", "my partner" or no match takes the account the person shares the most
  photos with and records that as an assumption. A name no account matches (`"grandpa"`) is kept as the name the
  film calls them, and the photos are the person's posts whose captions name them; when no caption names them either,
  every photo in the posts is used, and an `assumption:` line names each one and why. It writes the runner-up and the account the person talks to
  most, so a busy commenter is never mistaken for the named one. Then it collects **every photo and video the two
  share** (posts and reels that tag or mention them, stories with them, the named one's own posts that tag the
  person), **the comments they traded** (both sides, paired into a line and its answer) and the voice of each side,
  **the occasion** (their words first, then a caption such as "dani turns 30 on october 24" for the kind and the
  day; the age and an anniversary's years come from the person's words alone, and `--line` is the wish), **the first and the
  latest photo together**, **the eras** (chapters of the friendship by place and months) and **the love lines**
  (the person's own short lines to or about them). Output: `B/shared.json`, `B/ask.json`.
- `picks.py` prepares the shared photos (`B/photos/`, `B/picks.json` with each photo's era, its source and
  its analysis, plus the opener, first, latest and best chapters).
- `palette.py` reads three palettes: the person's own, the named one's (from their feed), and the one the two
  share, from the photos of them together. The film's colors come from the shared palette.

Output: `B/research.json`, a machine draft of `B/taste.json`, and `B/taste.draft.md` (what research
read, under the five headings, with the year's moments under "you are").

## Read it like a creative director, then write taste.md

Open `B/taste.draft.md` and look at a dozen of the shared photos (`B/photos/`) and a few of the named
one's own posts. Then write `B/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** the two of them: who the film is for, how you know (their words, the tags, the comments), the
  occasion, and the story of the friendship from the first photo to the latest, chapter by chapter: the moments of
  their year, what they did, where and with whom, the one the year turns on.
- **You like** what the two do together and what their photos are of; the shared palette and where each side's
  palette pulls it.
- **Your style is** the colors, light, texture and pacing the film should have, from both feeds.
- **Your voice is** how each of them writes, with two or three of their own lines quoted from each side.
- **Avoid** what would be wrong for them (cold grading, neon, jokes at the named one's expense, stock gloss,
  whatever the data says).

Use their photographs, their account names, their people and places, and their words. American spelling.

## Fix taste.json where the reading says otherwise

`B/taste.json` is a draft: correct anything your reading contradicts (`occasion` label and title, `pacing`,
`texture`, `avoid`, `pillars`, `music`, the `love_lines` list in the order they should play, the `moments`). Keep its keys; storyboard.py,
grade.py and the critics read them. Once you edit it, change `written_by`, so a rerun of research.py leaves your
version alone.

`moments` is the year the film tells, one entry per card, in date order: research.py drafts one per shared photo
post, from the caption, the people tagged or named in it, its place and its date, and the first two comments the two
left under it (`talk`); a tagged photograph with no caption is a wordless moment, its `name` and `line` empty, and its card
shows the photograph with only the lines the two traded under it, if any. Curate it as part of "You are": keep at
most the 15 that tell their year best, the ones where they did something, went somewhere, made something or were with
their people, over the ones that only describe a picture; a thinner year keeps every moment it has, and the wall
holds exactly them and the occasion photograph, one cell each. Give each captioned moment a `name`
in its caption's own words (`"the surfers were up before breakfast"` from "the surfers were up before breakfast and
so were we"; a name the caption does not hold falls back to the draft's), and set `"peak": true` on the one the year
turns on: it holds longest and is the film's middle still. Every other card holds as long as its photograph asks
(the people in it, whether it tags them, the words to read beside it). Never add a moment that is not one of their posts.

`music` is the brief that turns the chosen look's music recipe (`music.py make` plays the recipe of the look's style
card, turned by this brief, when the person placed no track of their own); correct it
the way you correct `register`, from what you read about them (their register, their pacing and texture, the places
and eras of the friendship, what they share) and from the film's theme (their year card by card, building to the age):

| key | what it holds |
|---|---|
| `tempo` | beats per minute, or null to leave it to the look: the engine takes the tempo of the recipe's range nearest this one, `snap` folds the film into that range, the hook's hit and the closer's fall and punch land on its beats, and the cards share the rest of the length by their holds |
| `styles` | three to six genre and instrument words that fit them (where they were, what they post, its texture); `music.py make` plays each instrument a style names (piano or keys, strings or a pad, guitar, bass, hand percussion, drums) and only those, and the recipe's own voices when the styles name none; a style word that names another recipe plays that recipe |
| `avoid` | what the music should never have, each written as a noun ("vocals", "big drops"); an instrument named here is never played |

Never an artist, a band or a song: a name is not a taste.

## Done when

`B/taste.md` has all five headings and `B/taste.json` matches it. storyboard.py refuses to run without
taste.md.
