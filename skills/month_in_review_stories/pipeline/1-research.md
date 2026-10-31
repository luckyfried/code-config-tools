# 1. Research: the month's moments, before making anything

Goal: the run's `month.json` (what the board builder composes), `taste.md` (one page, in prose) and the month's
moments picked into `taste.json`, written before any storyboard. The question this kit's research answers: what
happened this month, with whom and where, in their own words.

## Run the reading

```
python3 S/scripts/research.py
```

It reads the month's posts and writes, in the run's build folder:

- `month.json`: the handle and name, the month, and its posts and reels (day, type, caption, photograph, place, and
  the likes and comments each one has where the door gives them). Every word and every count on the cards comes from
  here; the handle is their username, from the account or from a `handle` or `username` column of a posts table.
- `stats.json` and `research.json`: the same posts with the people each caption tags and the place it names, and the
  words of their captions (case, length, emoji, hashtags).
- `taste.json`: their register (case, exclamation marks, hashtags), read by the caption draft and the brief, an
  `ask` draft (`{"counts": false, "seconds": null, "series": false}`), a `moments` draft: the month as its captions
  tell it, its first post and its last and, between them, the one whose caption says the most, that one the peak, and
  a `music` draft: what the music leaves out.
- `taste.draft.md`: the month post by post under the five headings below, each post with its caption, its place and
  its people and its figures.

It exits 4 when the month has fewer than three posts to tell it with, with the sentence to tell the person. A post
with no photograph stays in the month: it is told as a type card.

## Read it like a creative director, then write taste.md and pick the moments

Open `taste.draft.md`, open the month's photographs with the Read tool, and write `taste.md` beside it yourself: one
page, five paragraphs under these headings, exactly:

- **## you are**: who they are this month: the three or four best things that happened (what they did, made, went
  to, pulled off, or a person they did it with), each as its photograph, the place and the people, and the caption
  line that carries it; and which one is the peak, the one they would tell first.
- **## you like**: what their photographs keep returning to: the people, the places, the things.
- **## your style is**: the light, the color and the framing of their photographs, and the kind of month it was:
  a wedding month, a slow month, one big trip.
- **## your voice is**: how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **## avoid**: what would be wrong for them (shouting type, exclamation marks, a number they would never say).

Then set `ask` in `taste.json` from what they asked for, in their own words, and nothing more:

| field | set it to |
|---|---|
| `counts` | true when they ask for their top posts, their best performers, what did best, or their numbers on the cards |
| `seconds` | the reel's length when they name one ("a 15 second reel" is 15), as they said it, even outside 12 to 30 s (draft refuses that by name); otherwise null, and the reel runs 15 s |
| `series` | true only when they ask for the cards as one video as well; otherwise the cards are delivered one by one and no `series.mp4` is made |

Then replace the draft `moments` in `taste.json` with the ones under "you are": three or four, each `{"day": <the
post's day>, "photo": "<the post's photo, exactly as month.json names it, or null when it has none>", "what": "<what
happened, in a few words>", "line": "<the words it says on screen>", "peak": true|false}`, exactly one of them the
peak. Pick them for what happened, from their captions and their photographs: a wedding beats a coffee, a first time
beats another time, a person beats a view; likes and comments never choose a moment. The month decides the shape: one
big trip is told as its days, a slow month as its small things, a month with one event as the run-up and the day.
When `ask` says `counts`, each card also shows its count as month.json carries it; otherwise no count reaches the
screen. The line is theirs: their caption, or the part
of it that tells the moment, as they wrote it; a caption that only states a figure ("1000 followers") gives an empty
line, and that moment is wordless. A post with no photograph keeps `photo` null and is told as big type on the shared
ground; never make a stand-in picture for it. storyboard.py tells the cards in date order from these posts, and the reel
opens on the peak, then the others in date order; a photograph that is no post's is refused.

Then write each moment's `shot`, the clip an image-to-video model would make from its photograph, the way a
cinematographer writes a shot list: look at the photograph and fill in every field. `research.py` drafts the lens, the
height and the light from the photograph's measures; correct them from what you see, and write the subject and the
move yourself. A moment with no photograph has no shot.

| field | what it holds |
|---|---|
| `subject` | what the camera is on, as the photograph shows it, and what in it moves ("the sliced loaf on its board, crust up, steam rising off the cut") |
| `move` | the camera's move over the beat, written out and back so the loop closes ("a slow push in toward the crust and back"), or the subject's own motion with the camera still ("the camera still as her hands keep the beat"); no two moments in a row move the same way |
| `lens` | the lens and what it does ("85 mm, close, the background soft") |
| `height` | where the camera stands ("the camera low, looking up at her") |
| `light` | the light as it falls in the photograph, with the side it comes from ("warm low sun from the left") |

`research.py` drafts the light's side from where the photograph is brightest. Every request `clips.py list` writes
carries these, the beat's length, the 9:16 frame at 1080x1920 and a seamless loop that ends on its first frame, and
the reel's stand-in for the clip holds on the photograph with the same kind of move: a push for a move in, a pull for
a move out, a crane for a move up or down. `storyboard.py draft` refuses a moment whose shot has no subject or move.

The look they pick brings its own music, at the board's tempo, so the music brief in `taste.json` holds only what
they said about the music:

| field | what it holds |
|---|---|
| `styles` | empty, unless they say what the music should be; then their genre and instrument words ("warm felt piano", "brushed drums") |
| `avoid` | what the music leaves out ("vocals", "spoken word", and anything they said they do not want) |

Never an artist, a band or a song: describe the sound in genre and instrument words.

Use their words, their people and their places. American spelling.

## Done when

`month.json` exists, `taste.md` has all five headings, and `taste.json` carries their `ask`, three or four moments with
one peak, each with a photograph carrying its shot, and the music brief.
storyboard.py refuses to run without taste.md.
