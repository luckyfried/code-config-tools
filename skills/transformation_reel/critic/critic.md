# The critics

Three critics judge the three boards (movement 3); the motion designer reads the timed cut (movement 4); the motion
designer and the person score the cut (movement 5). Each one is a voice you take on in turn, with its own eye. Every
round is scored on the seven rules below, the bar every film from this kit is held to. Score what a viewer would notice, from what you can see and hear in this session, and say
why in plain words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: does one idea carry the film
and motivate every move; is there depth, light and one grade, or a photograph on a flat field; does the type move as
a designed system and stay inside the safe lines; does the camera have weight and does the rhythm vary; does the
sound sit where the picture lands. Answers the swap test and the timing round.

**The editor.** Cuts documentaries and social films. Looks at story: does every beat show something they made, does
the run from day one to the latest build, do the milestones read as turns and the peak hold longest, does the ending
land in their own words and hold still on the ask.

**The person.** Speaks in the first person, from `RUN/taste.md` and their captions: "is this me?" Their photographs,
their words, their colors, nothing on the avoid list. Would I post this today, without changing a thing?

## The seven rules (1-5 each)

The bar: a mean of 4.5 over the seven, and no rule under 4. A round's score on a rule is the lower of its critics'
scores.

| key | rule | a 5 | a 3 or lower |
|---|---|---|---|
| `concept` | R1 one idea, and every transition is motivated by it | the wall of what they made from the first frame to the last; each card lands in its tile and the camera follows the wall to the next | a slideshow: photographs sliding, whipping or fading in, an idea that appears only at the end |
| `image` | R2 depth, light and one grade | a card standing off the wall with its shadow, lit, the wall and its neighbors around it, every photograph under the look's one finish | a full-bleed photograph with nothing behind it; a bright shot beside a dark one with no shared finish |
| `type` | R3 type in motion, designed as a system | letters that enter and leave by design with tracking that resolves, a clear hierarchy, every word inside the safe lines | type that fades in and out, a word past the safe line, a trail crossing a settled line |
| `motion` | R4 motion with weight and a rhythm that varies | one continuous camera that winds up, travels and lands past its mark; moves that change from beat to beat; the peak holds longest; the closer holds still on the ask | one move repeated, blur that hides the frame, holds that wait, an ending that just stops |
| `sound` | R5 sound designed to the picture | a cue where each card lands, a riser into the closer, an impact on their words, the stop on the ask | a bed under pictures with no relation to them, a cue on nothing |
| `shots` | R6 the generated shots are the spectacle | six requests a cinematographer would write, each naming subject, move, lens, light, length and a seamless loop; the clips that arrived play on their cards | one template prompt per card, or requests nothing ever plays |
| `deliverable` | R7 the deliverable is unmistakable | `out/` holds the films, the then/now pair, the caption, the brief and a review page that opens on the film, with the caption, the other two looks and how it was made in plain words; nothing else | a page that opens on a warning, a then/now that is one picture, an empty table, stray files |

A rule you cannot read in this session is never scored as read. When nobody in the session can hear the film, put
`sound` in that critic's `not_read` and leave its score empty; the verdict and the brief say it was
not read. Never score sound from the cue table alone.

## The storyboard (movement 3)

Look at the board's four styleframes (`RUN/storyboards/drive/frames/hook.png`, `ordinary.png`, `dense.png`,
`closer.png`) and its sheet full size. Score them as each critic in turn in `RUN/vote/scores.json`, from the frames
you can see and nothing else. Write one paragraph per
critic, at least 25 words: what works, what fails, the one change you would make.

**The swap test** (the motion designer, on each styleframe): could another of their photographs stand in this
frame with nothing else changed? `holds` when the design is built on this photograph: the line on it is their own
caption for this piece, its tile and its date place it on the wall, the move answers where it sits. `swappable` when
the frame is a template with a photograph in it. A board with a swappable frame does not go on to the film.

## The four reads

Every film is held to four reads, and to one idea the camera follows from the hook to the closer:

- **carried**: one element carried across every transition (the card dropping into its tile, the wall of what
  they made filling); name what crosses each cut, and the cut where nothing does.
- **sound**: a sound where each card lands and nowhere else, under the music (a run lands lightly, a milestone and
  the latest land harder, the closer's words land on the whole wall and ring out into silence). This read needs
  ears: when nobody in the session can hear the draft, put `sound` in `not_read`.
- **belongs**: the motion belongs to the photograph (the swap test on the move): put another photograph under the
  same move and it stops making sense.
- **held**: one held thing per beat, the moment's photograph with their line on it: what each beat holds still for
  the eye, and the beat that holds two or none.

## The timed cut (movement 4)

Before anything is finished, the motion designer reads the rendered draft: `RUN/frames/strip-<beat>.png` (12 frames
across each beat), `RUN/frames/film-strip.png` (one frame a second), `RUN/draft/film.mp4` with its sound and
`RUN/draft/check.json` (the figures), with the four reads. Each read names the frames it saw. Watch for
a beat that reads the same as the one before, a run with no contrast, a hold that waits instead of holding, and a
frame where a flat field is the stage instead of the photograph.

Fill in `read` in `RUN/critic/timing.json` (`carried`, `sound`, `belongs`, `held`, `not_read`, `repeats`,
`verdict`) and run `vote.py timing` again. A beat named in `repeats` fails the round; a read in `not_read` is
recorded as not read, never as a pass.

## The cut (movement 5)

The motion designer and the person score the rendered cut. Look, actually look, at this cut, never the last one:

- `RUN/cut/film.mp4`, and `RUN/qa/strip.png` (the cut at 2 fps) with the Read tool; `vote.py cut` refuses until
  `RUN/qa/check.json` is the check of this cut, so the strip is this cut's;
- `RUN/cut/then-now.png` (day one beside the latest, the span between them) and the story cards
  `RUN/cut/stories/*.png` when they were asked for;
- `RUN/subject.json` (the first post, the latest, the milestones) against the dates on screen;
- `RUN/qa/check.json` (the measured checks), `RUN/render/report.json` and `RUN/clips/requests.json` (the shot
  requests).

Score `image` and `motion` from these frames and strips alone, never from a description of the film or an earlier
cut; the cut is what ships. Fill in
`RUN/critic/cut-<tone>-N.json` and run `vote.py verdict`. In each paragraph, name the worst thing you see.

## The verdict and the one fix

`vote.py verdict` states the round against the bar and answers one of three ways:

- `SHIP`: the cut meets the bar on every rule read. Deliver.
- `FIX ONCE`: a rule under the bar has a lever a run can pull, and the round is the first. The verdict names the
  rule and its lever. Take it: pull the lever, follow it through to `film.py render`, run `vote.py cut`, score the
  new cut, and run `vote.py verdict` again. Say in `fixed` what changed.
- `DELIVER WITH SCORES`: the one fix is spent, or no lever reaches the rules under the bar. Deliver this cut as the
  best the run made; the brief states every score against the bar, and the review page states none.

The verdict never stops a delivery; `deliver.py` refuses only on what `qa.py gate` measures.

## The levers

The builder lays every film out from the posts, so the levers are its inputs, never the board:

| rule | lever | then |
|---|---|---|
| `concept` | the subject, its posts and its milestones: `research.py --subject "..." [--terms ...]` | movements 1 to 5 again |
| `image` | the colors: `palette` in `RUN/taste.json` (the look's palette rule makes the film's colors from it) | movements 2 to 5 again, from `storyboard.py draft` (a new draft starts a new vote) |
| `type` | the look's type: the words' colors through `palette` in `RUN/taste.json`, or, when taste picked the look, another of the three looks (`vote.py pick <style>`, its faces and its type); a look the person chose stays | movements 2 to 5 again, from `storyboard.py draft` (a new draft starts a new vote) |
| `motion` | none inside a run: the camera, the holds and the rhythm are the board builder's, laid out from the posts | |
| `sound` | the music: another track at `RUN/music/source.<ext>` (`music.py find --origin "..."`), or the brief's `styles` and `avoid` in `RUN/taste.json` and `music.py make` | `music.py analyze` (a placed track only), `storyboard.py snap`, `music.py master`, `film.py draft`, `vote.py timing`, `film.py render` |
| `shots` | the generated clips: make each shot `RUN/clips/requests.json` asks for with the session's video model and save it at its `save_as` path | `film.py render`, `qa.py check`, `vote.py cut` |
| `deliverable` | the words around the film: `RUN/caption.md` | `deliver.py` |

A change to `RUN/taste.json` reaches the film only through a new draft: `film.py draft` and `film.py render` refuse
a board drafted from another `taste.json`.
