# The critic

The critic scores the film against the seven rules of studio grade below, R1 to R7, each 1 to 5. The bar is a mean
of 4.5 with no rule under 4. The panel judges the storyboard (movement 3), the editor reads the timed cut before the
film renders (movement 4), and the motion designer and the person score the rendered cut (movement 5). Each is a voice
you take on in turn, with its own eye. Score what a viewer would notice, and say why in plain words.

The gate reports and never blocks on a score: a film under the bar is delivered as the best cut, with every score
stated in the run's `brief.md`; no score ever appears on the review page. A score under 4 names the lever that fixes it; when no lever in the list below reaches
it, the lever is `none`, the budget is spent, and the film ships with that score stated.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Reads R1 to R4 and R6: one idea carried by the
dot and the route; every move the route's own act; depth in every moving shot; one grade; type that enters by word
and settles; a camera that anticipates and overshoots and never makes one move twice in a row. Applies the swap test
to every frame: it passes when their photographs, their places and their words move the frame, and fails when
another person's year would sit in it unchanged.

**The editor.** Cuts documentaries and social films. Reads R1, R4 and R5: does every beat show something they did;
does the year travel, with a sense of where it leaves from and where it comes back to; is there a turn, a peak and a
release; does each beat hold on its moment; is there a sound where each beat lands and nowhere else.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos, their
colors, their voice, their pacing, nothing on the avoid list. Reads R1 and R7: would I post this today, without
changing a thing, and is what I would post plainly there?

## The seven rules (1 to 5 each)

| key | standard | how the kit meets it (a 5) | measured by | a 3 or lower |
|---|---|---|---|---|
| `R1` | concept and motivated transitions: one idea from the first second, a motif on every beat that pays off in the closer, every move and cut one the style card allows, each the style's own act | the hook opens on the whole route, every pin set out and the dot on the first, under the year and their handle; the dot and the route it draws recur on every stop; every move between stops is the dot running the leg on their map, the route drawing behind it; each beat's move is the card's own for what the beat holds; the closer is the style's last frame (the poster, the title card, the book's cover) with the route through its window | frames: the hook, two stops, a move, the closer | a transition the card does not allow, or one that carries nothing across the cut; a motif that appears once; an ending that just stops |
| `R2` | image treatment: depth, light, one grade | the photograph moves inside its box through every hold (a slow push toward its focus and a drift the way the dot came, under the beat's own move) while the map turns under the camera; a shadow under every print standing off the map; the style card's finish and its one grade over every photograph, the map and the closer; the stand-in for an absent clip is that layered move; the closer's still stays still | frames: two frames of one hold, three stops side by side | a photograph sitting flat for a whole hold, stops in different color worlds, a finish the card does not give, a closer whose window shows no map |
| `R3` | type in motion, as a system | the card's two faces, its scale and its alignment, each word where the card's photo layout sets it; each line enters as the layout says (cut on, faded up, typed), settled within 1 s of its beat; every line inside the safe area; on the closer every name reads beside its pin and the route crosses none | frames: a stop's band, the closer | an entrance the card does not give, mixed alignment, a name under the route or over another |
| `R4` | motion and rhythm | one continuous camera; a small pull back before each move and an overshoot where it lands; consecutive moves differ (one climbs over the map until every place and the route stand in frame, the next comes down onto the map as the photograph folds away and rides the dot along the leg), and the map and the route show in every move; holds vary with what each photograph carries; the peak holds longest; the closer holds still and silent | the 12 fps strips; frames of consecutive moves | one move repeated stop after stop, nothing moving inside a hold |
| `R5` | sound to picture | a cue only where a beat lands; the effects 8 LU under the music; the music stops where the dot lands | `qa/check.json` (audio); the cue placement is a person's read while watching, so it is `unread` when nobody in the session can watch with sound | effects louder than the bed, a cue with nothing landing |
| `R6` | generated shots are the spectacle | `clips/requests.json` holds one request per shot, each written as a cinematographer would (subject, camera move, lens feel, height, light, the beat's seconds, a seamless loop), for the hook's world, the texture between chapters, and each still brought to life; no two requests share a template | `clips/requests.json` | one prompt pasted for every stop, a request with no move or no light |
| `R7` | the deliverable is unmistakable | `out/` holds the three films (9:16, 16:9, square), `post.png`, `story.png`, `caption.md`, `boards.png` and `review.html`, the page that opens on the film with the story card as its poster, the caption to copy, the two looks not picked with how to ask for one, and how it was made in plain words, with no score | the `out/` listing; `review.html` | process files beside the film, a page that shows a score or leads with a vote table |

## Scoring

- Score each round from that round's own frames: `vote.py cut` cuts into `critic/cut-N/` the film's first frame,
  sixteen frames at equal spacing, each beat as the camera leaves it, and each shape's closer at rest at full size,
  and the round lists every one it viewed in `seen`. A read never comes from a previous cut.
- R2 and R4 are read from rendered frames and strips only (`critic/cut-N/`, `frames/`, `qa/film-strip*`). A read
  that cites the storyboard, a plan, the name of a move, or the kit's own files instead of a frame is not a read:
  name the frame that shows it.
- A rule nobody in the session can read is `null`, with a sentence in `unread` naming why (for example R5's cue
  placement when nobody can watch with sound). It is stated as unread in `brief.md`, never passed.
- When a score is under 4, `lever` names the one change from the list below that fixes the worst rule (`name`, and
  `change` saying what to set) and the round runs again on the new film. `lever.name` is `none` when no lever below
  reaches it; the budget is spent and the film ships with its scores stated in `brief.md`.

## The storyboard (movement 3)

Look at each look's `storyboards/<style>/sheet.png` (the hook, the stop and the closer at rest; any frame full size
that you need is in `storyboards/<style>/frames/`), read its `storyboard.md` (per beat the move and the cut, what the
move reveals and what it carries across the cut, every sound cue at its beat, every clip request), and score each look
on R1 to R7 as each critic in turn in `vote/scores.json`. A storyboard is a promise: score the film it will become, from the frames you can see. Write one
paragraph per critic, at least 25 words: what works, what fails, the one change you would make. Then the swap test on
each look's three compositions, as the motion designer: a composition passes when another person's year would change
the frame (the region the map shows, the route the dot drew, the photograph, its place's name and their line, the
places named at the closer) and fails when any year's photographs would sit in it unchanged. A look that fails one
cannot win.

## The timed cut (movement 4, before the render)

As the editor, watch `preview/film.mp4` and open every strip (`preview/film-strip2.png` and every
`preview/film-strip12-NN.jpg`, the film at 12 frames a second) with the Read tool. Read it for
monotony: moves that repeat one shape stop after stop, one size or one length so the eye stops expecting anything; a
hold with nothing moving. Fill in `critic/timed.json`: `monotony.pass`, `monotony.read` (at least 25 words: where the
rhythm changes and where it does not) and `monotony.seen` (the name of every strip you opened; the read needs them
all). `film.py render` waits for it.

## The cut (movement 5)

The motion designer and the person score the rendered film on R1 to R7. Look, actually look:

- every frame in `critic/cut-N/` full size with the Read tool, and `qa/film-strip2.png` and every
  `qa/film-strip12-NN.jpg`;
- `out/` (the three films, `post.png`, `story.png`) and `frames/` (the hook, the stop and the closer of each format);
- `clips/requests.json` for R6, `qa/check.json` for R5.

Fill in `critic/cut-N.json` and run `vote.py verdict`.

## The levers

- A place that is wrong or missing: `places.py --add/--drop/--home/--rename`, `research.py`, `storyboard.py draft`.
- A photograph that is wrong for its place, or two that repeat each other: `cast.json` (keep each visit's `place` and
  `n`, change its `shots`), then `storyboard.py draft`.
- A caption that contradicts its photograph (a place named in it that the photograph does not show): the place is
  found from the caption before the photograph, so fix it where the place is found, `places.py --rename/--drop` or
  the visit's `place` in `cast.json`, then `storyboard.py draft`.
- The handle: `taste.json` `handle`, then `storyboard.py draft`. With no username in the data it is null and the film
  shows the year alone.
- A line that is not theirs, says nothing about the visit, or runs too long to read: the visit's `line` in
  `taste.json` `moments` (a caption of that visit, a clause of it, or null; another post's caption takes that post's
  key as `post`), then `storyboard.py draft`.
- A film whose peak is not the best moment of the year: `"peak": true` on that one visit in `taste.json` `moments`,
  then `storyboard.py draft`.
- The look: another of the three styles, `vote.py pick --board <1, 2 or 3>`, then the steps a pick reruns. The faces,
  the moves, the cuts, the grade, the grain and the closer are the style card's and are never set here.
- The colors: the year's palette in `taste.json` `palette.year`, which the card's palette rule makes the film's colors
  from, then `storyboard.py draft`.
- The music: another track at `music/source.<ext>` and `music.py find --origin "..."`, or `taste.json` `music` and
  `music.py find`, then `music.py analyze`, `storyboard.py snap`, `storyboard.py sheets`, `music.py master`.

After any lever, the film is made again from that step: the draft, the vote, `snap`, `sheets`, `music.py master`,
`clips.py list` and `normalize`, `film.py preview`, the timed read, `qa.py timed`, `film.py render`, then `vote.py cut`
for the next round. Words,
numbers and positions are solved by the builder from the trip and their lines; the levers change the trip, the cast,
the lines, the taste, the look or the music, never a board.
