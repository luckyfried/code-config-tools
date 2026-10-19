# 4. Produce: top-tier motion graphics, with their assets

Goal: `out/film.mp4` and every card in `out/cards/`: `NN-<role>.mp4` (the animated card) and `NN-<role>.png` (the
static card). The film and every animated card are 1080×1920, 30 fps, H.264 high, CRF 18, 15 s, with the music as
AAC 192 kbps at −14 LUFS; every static card is a 1080×1920 PNG. They are rendered by the kit's Remotion project
(`S/motion/`). Run movement 5 (`5-clips.md`) first: the film and the cards place the clips.

## Music

The music comes from whatever you or the person have. In order:

1. A track you can fetch or make: their own library, a platform music library you have access to, a music model.
   Save it as `build/music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. `music.py find` on its own takes the longest audio file of 15 s or more under the workspace (their library).
3. When find exits 3 (no music anywhere), `music.py make` writes a warm bed in the winning board's tempo and mood.

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

- `snap` moves every cut of the film and of every card onto a downbeat (or a beat), keeps each set at 15 s, and
  writes `build/film.json`, the renderer's input.
- `master` trims the music to 15 s and brings it to −14 LUFS integrated, true peak about −1.5 dB. One master plays
  under the film and under every animated card.
- `render` renders the film, every animated card and every static card in one browser session (about 50 s on a
  desktop for four cards), resolves each beat's clip id from `build/clips.json`, lays the music under every video,
  and writes `build/render-report.json` (any text outside its safe area, any font that failed, any job that failed
  after three tries), `build/timeline.json` and `build/cards.json`. Every animated card carries the series mark
  (the month and "02 / 04", one progress segment per card); the static card shows it full.
- `frames` writes one settled frame per card into `build/frames/NN-<role>.png` (taken from the beat the static is
  drawn from, past its entrance and before the cut out), six of the film into `build/frames/film-NN.png`, and the
  two rows together as `build/frames/sheet.png`.

The standards the stories are held to are in `S/design/standards.md`; the type scale, easing, transitions and safe
areas are the JSON files beside it. To change anything, edit the winner's `storyboard.json` (words, order, photos,
frames, transitions, prompts) and run `snap` and `render` again; never edit `build/film.json` by hand.

## When node could not be installed

`setup.py` reports `"engine": "stills"`. Then `film.py render` composes each beat as a still with Pillow and moves
it with eased pushes and crossfades in ffmpeg, from the same `film.json`; `build/engine.json` records it and
`brief.md` says so. Everything after this step is the same.

## Look before the critics do

Open `build/frames/sheet.png`, then every `build/frames/NN-*.png` full size with the Read tool. Text cut off or
caught half typed, a photo cropped past its subject, a card that looks unfinished, two cards that say the same
thing: fix it in the storyboard and render again now.
