# 4. Produce: the timed cut, read before it renders, then the film

Goal, in the run's `out/`: `film.mp4` (the reel, 1080x1920), `film-square.mp4` (1080x1080) and `film-wide.mp4`
(1920x1080), each 30 fps H.264 High with AAC 192 kbps at -14 LUFS, plus the best-nine image `best-nine.png`
(1080x1080) and the story card `story.png` (1080x1920). All of it is rendered by the kit's Remotion studio
composition (`S/motion/studio`) from the one cut storyboard.

## Music

The music comes from whatever you or the person have. In order:

1. A track you can fetch or make: their own library, a platform music library you have access to, a music model.
   Save it as the run's `music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. `music.py find` on its own takes the longest audio file of 30 s or more under the workspace (their library).
3. When find exits 3 (no music anywhere), `music.py make` writes a warm bed in the winning tone's mood and tempo.

```
python3 S/scripts/music.py find --run build/<stamp> || python3 S/scripts/music.py make --run build/<stamp>
python3 S/scripts/music.py analyze --run build/<stamp>
```

`analyze` finds onsets, tempo, beats and downbeats.

## The generated clips

```
python3 S/scripts/clips.py list --run build/<stamp>
python3 S/scripts/clips.py normalize --run build/<stamp> [--why "<why a clip did not arrive>"]
```

Run these after `snap`. `list` prints every clip the storyboard asks for, with its prompt, length, photograph and the
file to save. Generate each with the platform's image-to-video model from the named photograph and save it where
`list` says. `normalize` conforms what arrived to its photograph's size and its beat's length, and the film plays it
on that photograph's card. A clip that did not arrive stands in: the film makes the camera or depth move the
storyboard names on the still photograph, and `clips.json` and `brief.md` say which.

## Cut to the music, and read the cut before it renders

```
python3 S/scripts/storyboard.py snap --run build/<stamp>
python3 S/scripts/film.py preview --run build/<stamp>
python3 S/scripts/vote.py timed --run build/<stamp>
```

- `snap` times the winner's storyboard at the music's tempo (or half or double it, whichever keeps the cut in the
  length band nearest the tone's own tempo), so every cut lands on a beat, and writes `film.json`.
- `preview` renders the reel at half size into `preview/film.mp4` with its strips and measures it: the cuts as
  planned and as the picture shows them, cuts per minute, the luma line, the hook event's frame.
- `timed` writes `critic/timed.json`. As the editor (`S/critic/critic.md`, "The timed cut"), open
  `preview/film-strip2.png` (two frames a second) and fill in the monotony read: does the cut vary its sizes and its
  rhythm, or settle into one shot repeated. A read that fails names the beat; fix the cause in the `taste.json`
  words, then `preview` again.

```
python3 S/scripts/qa.py timed --run build/<stamp>
python3 S/scripts/music.py master --run build/<stamp>
python3 S/scripts/film.py render --run build/<stamp>
```

- `qa.py timed` checks the cut before it renders: the bounds check on all three formats, the length band, the hook
  in the first 30 frames, a preview of this cut, and the monotony read. It prints `TIMED GREEN`; `film.py render`
  refuses a cut it has not passed. Beside the checks it prints two figures from the preview, the cuts per minute
  and the luma line's seconds under 0.5, which the editor reads with the strip; neither passes or fails.
- `master` lays the storyboard's sound cues over the music (for drive: `hit`, `whoosh`, `riser`, `ticks` and
  `impact`, synthesised at their named beats), ducks the music under the heavy hits with `sidechain`, trims the mix to
  the film and brings it to -14 LUFS integrated, true peak about -1.5 dB. A board's `stop` cue cuts the music where
  the picture stops: the last hit rings out over the held wall and the rest of the film is silent. `music/fx.wav` is the cues alone.
- `render` renders the three formats of the one storyboard, lays the music under each, and takes the stills from
  the films' rest moments: the story card is the reel's closer at rest, the best-nine image the square's. The run's
  `frames/` holds the hook, the densest beat and the closer of every format. `render/film-report.json` lists every
  failed job, text outside its safe area and font that failed. On a machine with an NVIDIA graphics card the render
  runs on the card; elsewhere it runs on the processor, and the film is the same either way.

The standards the film is held to are in `S/design/standards.md`; the type, easing and safe areas are the JSON
files beside it. To change the film, change `taste.json` (the words) and run the steps again from `storyboard.py
draft`; never edit `film.json`, a board or anything in `out/` by hand.

## Look before the critics do

Open every `frames/<format>-<rest>.png`, `out/best-nine.png` and `out/story.png` with the Read tool. Text cut off, a
photograph cropped past its subject, a beat that looks unfinished: fix the cause and render again now.
