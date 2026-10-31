# 2. Plan: the next nine, in order, in their voice

Goal: `plan.json` and `plan.md`: the next posts in posting order, each with its photo, its crops, the day it goes
up, a caption in their voice and the shot that brings it to life, and the film's hook, ask and world.

## Draft

```
python3 S/scripts/plan.py draft
```

`draft` takes up to nine photos from the pool in `picks.json` (their photos that never had a grid spot of their own;
the named folder alone when gather.py had `--photos`), never two from one post and never two near copies. It places
them as a tonal checkerboard by the detail of each photo's 3:4 grid cell: the calm ones on the corners and the
center, the detailed ones between them, so two busy frames never touch. Post 1 goes up first and ends at the bottom
right of the posts; the last lands at the top left. When fewer than nine photos fit, the plan has fewer posts and
everything after it shows the posts it has.

Each post gets its focal point (`focal`, [x, y] as fractions of the photo, read from where its detail gathers), its 4:5
post crop and its 3:4 grid crop centered on it, the post of theirs it follows, a date from their own cadence (the weekday they post most, their median gap between posts) and a draft
caption: the words that came with that photo, or none.

## Write the captions from the photographs

The drafts are often an old caption word for word, and a photo with no words of its own drafts none. Open each post's
photograph and write its caption as the moment it shows: what they are doing, where, and with whom, from what is in
the picture and the words, place and tagged people it came with; never a file name, a folder name or a source's
title, which often name another place or thing than the picture shows. On a post the film
holds on, the band carries the words the photograph came with (its post's caption, or in a folder they named, the note
beside it or its embedded description), whole, and with none, the caption you write here. Where their line runs too
long for its band, or reads wrong on screen, set the line of theirs the film carries in `taste.json` `"said"`, keyed by
the photograph's library path (`source` in `plan.json`), and draft again. Then put it in their voice from the
captions quoted in `taste.md`: their case, their length, their emoji or none, true to the day it goes up. Name a place
only when the photograph shows it or the words it came with name it. A caption the photograph contradicts is fixed here, at its cause. Edit the `caption` fields of `plan.json` (and `hashtags`, two or three of their own).

A post can carry a `lesson`: a short title set on its cover, the way their text posts are. Add one only when the audit
shows their text posts are saved.

## Write each post's shot and the film's words

Every post carries a `shot`: the shot a cinematographer would ask for to bring its photograph to life, written from
the photograph you opened, never the caption pasted in. Name its subject in six words or more, the lens in mm and the
camera's height the photograph was taken at, and its light ("the cup and saucer on the marble sill, 50 mm at eye
level, soft north window light"). The film holds on the first post, the middle one (post 5 of nine) and the last, and
passes the others in a beat; on a passed post the shot is the texture between chapters, a close look at a surface
that photograph shows ("the foam's cocoa dusting, 100 mm from above, raking window light"), and two posts passed one
after the other never share a lens (the steam over the cup at 60 mm, then the crust's flour at 35 mm). `clips.py list`
turns each shot into the clip request for its beat.

The film's own words go in `film`, in their voice and their case, never a date or a number:
- `hook`, two to seven words that state the glow-up, set letter by letter on the hook's band in the first second;
- `ask`, two to seven words the closer's header holds on under their handle and bio (what they want a visitor to do
  or feel once the new nine are up);
- `world`, the shot of the world their grid comes from, played under the hook: clip 00, made from the old post the
  hook's frame lands on, so write it from that photograph: its subject in eight words or more, the lens in mm, the
  camera's height and its light.

```
python3 S/scripts/plan.py check
```

`check` recomputes each post's crops from its `focal` and draws them on `crops.png`: every photograph whole, its
4:5 post crop in white and the box the film closes onto in orange. Open it. Where a box cuts the subject the caption
names (a face, the tower, the surfer), move that post's `focal` onto the subject and run `check` again.

`check` refuses posts out of order or on dates that do not rise, and a caption that is empty, a placeholder, too long,
out of their register, a repeat of another, or word for word the caption of a post already on their grid; a shot or a
world that misses its subject, lens, height or light, two passed posts in a row on one lens, and a hook or an ask
that is not two to seven words in their register. It runs the
critic's swap test on the cells as planned: a photo you moved or a focal point you changed can leave a calm post no
calmer than a busy one beside it, and the fix is to give the two posts each other's photo, caption and focal point. It
writes `plan.md`.

## Done when

`plan.py check` passes, every caption says what its photograph shows in their voice, every shot is the one its
photograph asks for, and every orange box on `crops.png` holds its subject.
