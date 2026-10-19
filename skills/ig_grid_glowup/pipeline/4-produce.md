# 4. Plan and produce: the nine posts, the grid after, and the before-and-after film

Goal: `out/plan.md` (the nine in posting order with dates and captions in their voice), `out/posts/01..09.png`
(1080×1350 each), `out/grid-after.png` (their profile with the nine in place over the real grid) and
`out/film.mp4` (1080×1920, 30 fps, H.264 high, CRF 18, AAC 192 kbps, −14 LUFS, 15 s), rendered by the kit's
Remotion project (`S/motion/`). Run movement 5 (`5-clips.md`) first: the film places the clips.

## The plan first

```
python3 S/scripts/plan.py draft
```

`draft` puts the winning direction's nine in posting order, dates them from their own cadence (the weekday and hour
they post most, their usual gap between posts) and gives each a draft caption: the words that came with that photo,
or the nearest post's. The drafts are a starting point and often an old post's caption word for word. Read the
captions in `build/taste.md` and write each of the nine fresh in their voice: their case, their length, their
emoji or none, about what is in that post, true to the day it goes up. Edit the `caption` fields of
`build/plan.json` (and `hashtags`, two or three of their own), then:

```
python3 S/scripts/plan.py check
```

`check` refuses a caption that is empty, a placeholder, over 40 words, out of their case, a repeat of another,
naming a weekday other than the day it goes up, or word for word the caption of a post already on their grid, and
writes `out/plan.md`. The film carries these captions, so the plan comes before `snap`.

## Music

The music comes from whatever you or the person have. In order:

1. A track you can fetch or make: their own library, a platform music library you have access to, a music model.
   Save it as `build/music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. `music.py find` on its own takes the longest audio file of 30 s or more under the workspace (their library).
3. When find exits 3 (no music anywhere), `music.py make` writes a warm bed in the winning direction's tempo and
   mood.

```
python3 S/scripts/music.py find || python3 S/scripts/music.py make
python3 S/scripts/music.py analyze
```

## Cut to the music, master, render

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master --seconds 15
python3 S/scripts/film.py render
python3 S/scripts/film.py frames
```

- `snap` moves every cut onto a downbeat (or a beat), takes the plan's captions into the nine, keeps the film at
  450 frames, and writes `build/film.json`, the renderer's props.
- `master` trims the music to the film and brings it to −14 LUFS integrated, true peak about −1.5 dB.
- `render` renders the nine posts, the grid after and the film in one browser session (about 20 s on a desktop),
  lays the music under the picture, and writes `build/render-report.json` (any text outside its safe area, any
  font that failed, any job that failed after three tries), `build/timeline.json` and `build/nine.json`.
- `frames` writes one settled frame per beat into `build/frames/NN-<beat>.png` (and every shot of a beat that holds
  several, such as the nine landing, into `build/frames/NN-<beat>/`).

The standards are in `S/design/standards.md`; the type scale, easing, transitions and safe areas are the JSON files
beside it. To change a post or the film, edit the winner's `storyboard.json` and run `snap` and `render` again;
never edit `build/film.json` by hand.

## When node could not be installed

`setup.py` reports `"engine": "stills"`. Then `film.py render` draws the posts and the grid with Pillow and moves
the film's beats with eased pushes and crossfades in ffmpeg, from the same `film.json`; `build/engine.json` records
it and `brief.md` says so. Everything after this step is the same.

## Look before the critics do

Open every `out/posts/NN.png`, `out/grid-after.png` and every `build/frames/NN-*.png` with the Read tool. A photo
cropped past its subject, type that looks like a default, two of the nine that read as one, text cut off, a beat
that looks unfinished: fix it in the storyboard and render again now.
