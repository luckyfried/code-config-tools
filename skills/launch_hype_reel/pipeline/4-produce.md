# 4. Produce: top-tier motion graphics, with the product's own assets

Goal: `out/film.mp4` (1080×1920, 30 fps, H.264 high, CRF 18, AAC 192 kbps, −14 LUFS, 15–30 s), the three teaser
stories `out/story-1.png`, `story-2.png`, `story-3.png` and the countdown card `out/countdown.png` (each 1080×1920),
and the feed post `out/feed.png` (1080×1350), all rendered from one storyboard by the kit's Remotion project
(`S/motion/`). Run movement 5 (`5-clips.md`) first: the film places the clips.

## Music

The music comes from whatever you or the person have. In order:

1. A track you can fetch or make: their own library, a platform music library you have access to, a music model.
   Save it as `build/music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. `music.py find` on its own takes the longest audio file of 30 s or more under the workspace (their library).
3. When find exits 3 (no music anywhere), `music.py make` writes a bed in the winning board's tempo and mood.

```
python3 S/scripts/music.py find || python3 S/scripts/music.py make
python3 S/scripts/music.py analyze
```

`analyze` finds onsets, tempo, beats and downbeats.

## Cut to the music, master, render

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/film.py render
python3 S/scripts/film.py frames
```

- `snap` moves every cut onto a downbeat (or a beat) and writes `build/film.json`, the renderer's props, with the
  clips from `build/clips.json` resolved into their beats.
- `master` trims the music to the film and brings it to −14 LUFS integrated, true peak about −1.5 dB.
- `render` renders the film and the five stills in one browser session (about 20 to 60 s on a desktop, longer with
  many clips), lays the music under the picture, and writes `build/render-report.json` (any text outside its safe
  area, any font that failed, any job that failed after three tries), `build/timeline.json` and `build/cards.json`
  (each still, its format and the beat it came from).
- `frames` writes one settled frame per beat into `build/frames/NN-<beat>.png` (and every shot of a beat that holds
  several, such as the days falling in a date beat, into `build/frames/NN-<beat>/`).

The standards the film is held to are in `S/design/standards.md`; the type scale, easing, transitions and safe
areas (reel, story and feed) are the JSON files beside it. To change the film or a card, edit the winner's
`storyboard.json` (words, order, frames, transitions, prompts, the cards) and run `snap` and `render` again; never
edit `build/film.json` by hand.

## When node could not be installed

`setup.py` reports `"engine": "stills"`. Then `film.py render` composes each beat and each card as a still with
Pillow and moves the beats with eased pushes and crossfades in ffmpeg, from the same `film.json`;
`build/engine.json` records it and `brief.md` says so. Everything after this step is the same.

## Look before the critics do

Open every `build/frames/NN-*.png`, the three stories, `out/countdown.png` and `out/feed.png` with the Read tool.
Text cut off, a product cropped past itself, a date that is hard to read, a tease that gives nothing away or a
reveal that shows nothing new: fix it in the storyboard and render again now.
