# The standard

Every film this kit makes is held to the rules below. This file is the same in every kit that shares the motion system:
it is written in one place and copied, and a copy that differs is refused, so a kit never edits its copy. The look of a
film is not set here. It is set by the style card the board is made in (`styles/<id>.json`): its two faces, its palette
rule, its moves and cuts, its easing, its finish, and its closer. A film is judged against its own card, and each of the
six cards meets these rules by design: a card that is followed is a pass. `critic/critic.md` is the procedure: who
reads, in what order, and where each read is written.

Each rule names its evidence; a rule whose evidence is a frame is read from frames, and no other.

| rule | evidence |
|---|---|
| R1 one idea, carried by the card's moves | frames |
| R2 the picture in the card's finish | frames |
| R3 type that reads, in the card's faces | frames |
| R4 motion and rhythm | frames and the strip |
| R5 sound to picture | `qa/check.json` for loudness; the cue placement is read by a person watching |
| R6 generated shots are the spectacle | `clips/requests.json` |
| R7 the deliverable is unmistakable | the `out/` listing |

## Reads and the bar

- The critic reads each rule from that rule's evidence and writes, for each, whether it passes and, when it does not,
  the clause it misses and the frame or file that shows it, so the next cut knows what to change.
- The bar: every rule passes, and the film is its own (the last section).
- Every read is of the film being read: its frames and strips are cut after its last render, and `qa/check.json` is
  measured after it. A read made for another cut is not a read of this one.
- R1 to R4 are read from rendered frames and strips only. A read that cites a storyboard, a plan, a move name, or
  "within my files" is not a pass.
- A read nobody in the session can make is written as not read, with the reason; it never counts as a pass.
- The gate reports every rule against the bar and never blocks on it. A film under the bar is delivered as the best
  cut. A rule under the bar that no lever in the run reaches is a spent budget, never a refusal.

## R1 One idea, carried by the card's moves

One idea carries the film: the hook states it in the first second, and the closer pays it off. Each beat moves by one
of its card's moves and each cut is one of its card's cuts, chosen by the board from what the beat holds (its form, its
words, its photograph), never by turn.

The critic's read: the frames of the first second, one frame of every beat, the frames across every cut, and the closer
at rest. A pass: the first second's frames state the idea; every beat's move and every cut is one the card names; the
closer pays the idea off. Not a pass: a first second with no idea in it, a move or a cut the card does not name, or a
closer that does not pay the idea off.

## R2 The picture in the card's finish

The film has one finish, its card's: the grade, the grain, the vignette, the bloom, the dust, the blur, the cadence,
the letterbox, each at the card's value, zero included. Every color on screen is a photograph's own or one the card's
palette rule made from the photographs. The closer's still is deliberate and stays still.

The critic's read: three beats side by side, a 1:1 crop of a moving frame and of a held frame, the closer's frames after
it settles. A pass: the beats are in one finish and it is the card's; every color is a photograph's or the palette's;
the closer's frames do not move. Not a pass: a beat in another finish from its neighbors, a color the card's palette
rule did not produce, or a closer that drifts.

Built by: the motion system (`motion/system/`, the files every kit shares) builds the finish from the card and the
closer's stillness; the palette module makes the colors from `taste.json` by the card's rule.

## R3 Type that reads, in the card's faces

Two faces, the card's; a scale; hierarchy by size and weight. Every line is legible at the size it is shown: it stands
on its ground at a contrast a person reads at a glance, it is on screen long enough to read, and the headline is
settled within one second of its beat. Every line at rest is inside the safe area of the profile, and nothing collides.

The critic's read: the frames at about 0.1, 0.5, and 1.0 s after each headline's beat, and every beat at rest at full
size. A pass: the card's two faces on one scale, the hierarchy by size and weight; every line readable against what is
behind it; by one second the headline is settled; at rest every line is inside the safe area and touches no other line,
no subject, and no edge of the frame. Not a pass: a third face, a line that cannot be read against its ground, a
headline still moving after one second, a line outside the safe area at rest, or a line over another line or over a
subject.

## R4 Motion and rhythm

The camera moves on the card's easing and lean. No two consecutive beats make the same move. Beats vary in length; a
fast run is followed by a held composition; the peak holds longest; the closer holds still and silent after the ask.

The critic's read: a strip of every move at 10 frames a second, the beats' lengths in the strip, and the closer's last
seconds. A pass: no two consecutive beats make the same move; the beats differ in length, a fast run is followed by a
held composition, and the peak's beat is the longest; after the ask the closer's frames do not move (its silence is
read with R5's evidence). Not a pass: the same move on two beats in a row, beats of one length, a peak no longer than
the others, or a closer that drifts.

## R5 Sound to picture

A cue only where a beat lands; effects 8 LU under the music; the bed from the card; the music stops where the ask lands.

The critic's read: the loudness row of `qa/check.json`, and the film watched with its sound. A pass: the loudness row
passes with the effects 8 LU under the music; a person watching hears a cue only where a beat lands, the bed the card
names, and the music stopping where the ask lands. When nobody in the session can watch with sound, the cue placement
is not read: the read is the loudness alone, and the review page says the cue placement was not read. A cue table, a
storyboard's sound lines, or a picture of the waveform is never a read of the cue placement. Not a pass: a loudness row
that fails, a cue with nothing landing, a landing that has no cue, or music running past the ask.

## Truthful content

Every word on screen is a word the person gave: the title, the handle, the sign-off, a beat's line, a beat's label. No
move, cut, or closer adds a word of its own ("the end", a date the person did not give, a caption). Every photograph is
the person's; a generated shot is built from the photograph it brings to life and says nothing the photograph does not
show.

## R6 Generated shots are the spectacle

Each clip request is a shot a cinematographer would write: subject, camera move, lens feel, light, the beat's
duration, seamless and loopable (the film loops a short clip; nothing else is asked). The hook's world, texture between
chapters, and a still brought to life are the three uses.

The shape of a clip request. Every request names its use (the hook's world, texture between chapters, or a still
brought to life) and these six parts:

| part | what the request says |
|---|---|
| subject | what the shot shows |
| move | the camera's move |
| lens | the lens feel |
| light | the light |
| duration | the beat's duration, in seconds |
| loop | that the shot is seamless and loops |

The critic's read: every request in `clips/requests.json`. A pass: every request names its use and all six parts,
written for its own shot. Not a pass: a request missing a part, a sentence other than the loop part repeated across
requests, a pasted caption or handle, a still brought to life whose subject its photograph does not show, or a request
that asks for more than the one looping shot (text, a cut, a second shot).

## R7 The deliverable is unmistakable

`out/` holds the films (one per shape), the posted image, the story card, the caption, and the review page as the
film's cover, and nothing a viewer could mistake for the product.

The deliverable list. `out/` holds:

- the films, one per shape the person asked for;
- the posted image;
- the story card, when the kit makes one or the person asked for one;
- the caption, or the description where the film plays outside a social feed;
- the review page, which opens on the film as its cover;
- any further piece the person asked for that the kit's `SKILL.md` names.

The brief, the storyboards and their sheets, the vote, the frames, and every other working file stay in the run folder.

The critic's read: the `out/` listing, and the review page opened. A pass: every piece on the list is there, and
nothing else is. Not a pass: a piece missing (a shape the person asked for, the posted image, a story card the kit
makes or the person asked for), a working file in `out/`, or a review page that opens on anything but the film.

## Its own film

The bar has a second half: this kit's film is its own and never another kit's. Two films whose hook and closer read as
one style both fail. A kit's films are made in the style cards its boards name, and the three boards of a run are in
three cards that share no more than two of the six axes (family, palette, camera, transition, finish, music), so a
viewer who has seen another film sees different work. The shared files (the motion system, the cards, and this
standard) carry the looks; a kit carries its story, its pieces, and any move of its own it registers.

The critic's read: the frames of the first second and of the closer at rest, beside the same frames of another film.
A pass: the two hooks and the two closers read as different work, in type, palette, move, and closer. Not a pass: a
hook and a closer that read as one style with another film's, which fails both. A run that holds no other film writes
this read as not read.
