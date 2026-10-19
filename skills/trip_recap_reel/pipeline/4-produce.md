# 4. Produce: top-tier motion graphics, with their assets

Goal: `out/film.mp4` (1080×1920, 30 fps, H.264 high, CRF 18, AAC 192 kbps, −14 LUFS, 30–60 s), the same cut
`out/film-16x9.mp4` (1920×1080, the same length) and five story cards `out/story-1.png` .. `out/story-5.png`
(1080×1920), rendered by the kit's Remotion project (`S/motion/`) from one storyboard. Run movement 5
(`5-clips.md`) first: the film places the clips.

## Music

The music comes from whatever you or the person have. In order:

1. A track you can fetch or make: the track on their travel posts (`build/research.json` `music`) when you can
   reach it, their own library, a platform music library you have access to, a music model.
   Save it as `build/music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. `music.py find` on its own takes the longest audio file of 30 s or more under the workspace (their library).
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

- `snap` moves every cut onto a downbeat (or a beat) and writes `build/film.json`, the renderer's props, with the
  clips from `build/clips.json` resolved into their beats.
- `master` trims the music to the film and brings it to −14 LUFS integrated, true peak about −1.5 dB.
- `render` renders both films and the five story cards in one browser session (about one to two minutes on a
  desktop for a 45 s film, longer with many clips), lays the music under both pictures, and writes
  `build/render-report.json` (any text outside its safe area in either frame, any font that failed, any job that
  failed after three tries) and `build/timeline.json`. The route map is drawn from the trip's coordinates; nothing
  is fetched.
- `frames` writes one settled frame per beat of the 9:16 film into `build/frames/NN-<beat>.png` (and every shot of
  a beat that holds several, such as a day's photos, into `build/frames/NN-<beat>/`); `film.py frames --film
  out/film-16x9.mp4 --out build/frames-16x9` does the same for the wide cut.

The standards the film is held to are in `S/design/standards.md`; the type scale, easing, transitions and safe
areas are the JSON files beside it. To change the film, edit the winner's `storyboard.json` (words, order, frames,
transitions, prompts) and run `snap` and `render` again; never edit `build/film.json` by hand.

## When node could not be installed

`setup.py` reports `"engine": "stills"`. Then `film.py render` composes each beat as a still with Pillow and moves
it with eased pushes and crossfades in ffmpeg, from the same `film.json`; `build/engine.json` records it and
`brief.md` says so. Everything after this step is the same.

## Look before the critics do

Open every `build/frames/NN-*.png`, the wide cut's frames and the five story cards with the Read tool. Text cut
off, a photo cropped past its subject, a beat that looks unfinished, map labels on top of each other, a wide frame
where the words sit on the map: fix it in the storyboard and render again now.
