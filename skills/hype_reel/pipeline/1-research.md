# 1. Research: inspect the subject and learn who they are, then plan, before making anything

Goal: `taste.md` (one page, in prose) and `taste.json` with its `plan`, written before any storyboard. Everything
downstream reads taste first. The questions this kit's research answers: what the subject is and what is true and
striking about it, how the person sees it and speaks, what the subject looks like, and where its colors meet theirs.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts:

- **moments**: every photograph of theirs they wrote words with, by its path, in date order, with the people they
  tagged, the place they named, whether it is of the making (their words name a step of it or the subject, or it shows
  the studio) and its `line`, drafted as their whole caption. These are the film's beats;
- **response** and **hooks**: the posts that drew the most comments plus saves and their opening lines, for the
  written brief only; the film never reads them;
- **the subject**: its name, kind, handle, its facts and its page text, a launch and its date (the days to go) when
  there is one, the pictures (a folder, a link, or only their posts) and the posts already about it;
- **the two palettes**: their year's colors, the subject's colors from its own stills, and where the two meet;
- their caption statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph,
  cadence, how long their reels run and how fast they cut, their people and places.

Output: `research.json`, a machine draft of `taste.json`, and `taste.draft.md` (the numbers under
the six headings).

## Read it like a creative director, then write taste.md

Open `taste.draft.md`, look at a dozen of their photos (`photos/`) and every subject still
(`library/subject/stills/`). Then write `taste.md` yourself, one page, six sections headed exactly:

- `## you are`: who they are this year, told as what they did, and how they come to the subject: they made it (the
  steps of making it in order, each as its photograph, the day and their own line), it is their friend, or they follow
  it and why.
- `## you like`: what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- `## your style is`: their colors, light, texture, pacing.
- `## your voice is`: how they write: case, length, emoji, punctuation, two or three of their own lines quoted, and
  their lines about the subject word for word.
- `## the subject`: what it is, the true facts about it in its own words or theirs, what its pictures show, its
  palette against theirs and the colors the film will live in, what they themselves said about it or who it is for,
  and, for a launch, the date as they gave it.
- `## avoid`: what would be wrong for them (neon, shouting type, stock gloss, whatever the data says), and for the
  subject (its colors are never graded away).

Use their account names, their places and their words; a number belongs in taste.md only when they would say it
themselves. American spelling.

## Inspect, then plan

Before any board, answer six questions in `taste.json` `plan`, each from the subject's own words, the person's, or a
fact its page states, never invented:

| key | the question |
|---|---|
| `what` | what it is, in one plain sentence a stranger understands |
| `for` | who it is for, or who would love it |
| `apart` | what sets it apart from everything like it |
| `claim` | the funniest or most impressive true claim (a number only when the subject or the person states it) |
| `hook` | the line the first two seconds carry, planned first: it says what this is about |
| `share` | the share caption: one to three sentences someone could post with the reel |

Then plan the film: `angle` (the one idea, "played as a movie trailer", "as a deadpan product launch"), `punchline`
(the closer's last line when it is not a launch; a launch's closer carries the date), and `tone`, one of default,
polished, yc-parody, chaotic, deadpan, cinematic, app-store (an idea picked in movement 0 brings its tone). The
draft fills what the subject's facts give and leaves the rest null; fill every one. No email address, phone number,
private message or other private detail goes into any answer.

## Fix taste.json where the reading says otherwise

`taste.json` is a draft: correct anything your reading contradicts. The films read three things from it: `palette`
(theirs and the subject's: the grade on their photographs sits where the two meet, and the films' colors
are the subject's own, measured from its stills, with theirs beside them), `moments` (what they did, which taste.md
tells) and `register` (their case: a lowercase writer's films are lowercase). `texture.grain` gives the grade a lifted black. Correct `music` the way you correct
`register`: it is the brief their film's music is made from (see below). Put what the person said in the request in
`said`: `said.subject` (how they describe it), `said.audience` (who it is for), `said.hook` (a line of theirs they
asked to lead with: it opens the film over their latest photograph of the making); their words replace anything
inferred. A length they asked for goes in `seconds`, in seconds (`20` for "a 20-second reel"), and stays `null` when
they named none: the film runs that length, and an ask outside 15 to 25 seconds makes the nearest length it can, with
one line in `out/brief.md` saying so. `subject.lines` holds the line each of the subject's pictures may carry (its own
words, else its facts in turn): cut or clear any. Curate every moment's `line`: it is what the film says on that photograph, word for word theirs, cut from the
whole caption the draft carries (all of it, or the one sentence of it that tells the moment, the hook's sentence about
making it among them); a long line is set smaller until it fits its beat, so the cut to what the beat says is made
here; a caption that says only a figure ("1000 followers") gets an empty line, and an empty line leaves the photograph
wordless. Nothing is ever written for them. Never change the subject's date or their words: those are in `library.json`. Keep its keys; the board builder,
the grade, deliver.py and the critics read them.

## Their music brief

`taste.json` `music` is `{"mood", "tempo", "styles", "avoid"}`, drafted from their texture and pacing:

| field | what it is | the draft |
|---|---|---|
| `mood` | one of `calm`, `drive`, `film` (the beds `music.py` makes) | `film` for a film-grain feed, `calm` for a slow one, else `drive` |
| `tempo` | beats per minute | 100; keep it where the film runs 15 to 25 s (about 90 to 130); an asked length moves it by less than a beat's worth |
| `styles` | three to six genre and instrument words | the mood's own |
| `avoid` | words the music never has | vocals, spoken word, harsh distortion |

Correct it from what you read: their places, their eras, their pillars, the light and texture of their photographs,
and the plan's tone (the film builds to the reveal and peaks there; a chaotic tone runs hot from the first frame). A music attribution in their
export gives genre words only. Never write an artist, a band or a song: the brief names what the music sounds like.

## Done when

`taste.md` has all six headings, `taste.json` matches it, and every key of `plan` is filled. storyboard.py refuses to run without
taste.md.
