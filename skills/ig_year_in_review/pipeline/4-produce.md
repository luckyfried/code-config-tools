# 4. Produce: the timed cut, read before it renders, then the film

Goal, in `out/`: `film.mp4` (1080x1920, 30 fps, H.264 High, AAC 192 kbps at -14 LUFS, 6 to 90 s), the ten carousel
cards in `out/carousel/` (1080x1350), the three story cards in `out/stories/` (1080x1920), and the review page's strip
in `out/strip/` (the hook, six months and the closer, 540x960). All of it is rendered by the kit's studio composition
(`S/motion/studio`) from the one cut storyboard, and every card is a frame of the film at rest, so the cards carry the
film's photographs and type.

## Music

The music is theirs: the track they chose, else a bed composed for the picked look. `find` takes them in that order:

1. A track the person gave you or asked for: save it as `build/music/source.<ext>` and run
   `music.py find --origin "<where it came from>"`.
2. Otherwise `find` composes a bed on real instruments from the picked look's own music recipe (its style card's
   `music`), turned by their brief (`taste.json` `music`: sound words, a tempo, what to avoid), its key from their
   palette and its sections on the board's impacts. `music.json`'s origin says which.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds onsets, tempo, beats and downbeats and writes them to `build/music.json`.

## Cut to the music

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/clips.py list
python3 S/scripts/clips.py normalize [--why "<why a clip did not arrive>"]
python3 S/scripts/film.py preview
```

- `snap` cuts the board that won the vote (`build/winner.json`) and refuses with no winner. It times the storyboard
  at the music's tempo (or half or double it, whichever runs nearest the look's own tempo), so every cut and every sound lands on a beat, and writes `build/film.json`.
- `list` prints every clip the storyboard asks for, with its prompt, length, photograph and the file to save.
  Generate each with the platform's image-to-video model from the named photograph and save it where `list` says.
  `normalize` conforms what arrived to its photograph and its beat. A clip that did not arrive stands in: the film
  makes the look's own move on the still photograph, and `clips.json` and `brief.md` say which and why.
- `preview` renders the reel at half size into `build/preview/film.mp4` with its strips and measures it: the cuts as
  planned and as the picture shows them, cuts per minute, the luma line, the hook event's frame.

## Read the cut before it renders

```
python3 S/scripts/vote.py timed
python3 S/scripts/qa.py timed
```

`timed` writes `build/critic/timed.json`. As the editor (`S/critic/critic.md`, "The four reads"), watch the
preview and its strips and fill in the four reads from what the film shows and plays: one element carried across every transition, a sound where
each beat lands and nowhere else, under the music, the motion belonging to the photograph,
and one held thing per beat. A read that fails names the beat; fix the cause (the words in `taste.json`, a line or a
scene in `picks.json`) and run from `storyboard.py draft` again, through the ballot and the tally.

`qa.py timed` checks the cut: no finding on the board, the length band, the hook inside the first 30 frames, a preview
of this cut, and the four reads passed. It prints `TIMED GREEN`; `film.py render` refuses a cut it has not passed.

## Master and render

```
python3 S/scripts/music.py master
python3 S/scripts/film.py render
```

- `master` lays the storyboard's sound cues under the music (`hit`, `riser`, `impact`, each played in the bed's own
  instruments where its beat lands), the effects scaled by loudness to `FX_UNDER_BED_LU` (8.5) LU under the bed, and brings the mix to -14 LUFS
  integrated, true peak about -1.5 dB. It prints both loudness numbers, writes them to `music.json` and to
  `storyboard.md`'s `Mixed:` line, and the gate's audio row is red when the effects sit less than `FX_LEAST_LU` (8) LU under. The board's `stop` cue cuts the music where the sign-off lands: the ending's impact
  rings out over the held frame and the last two seconds are silent. `music/bed.wav` is the music trimmed to the film, `music/fx.wav` the cues alone.
- `render` renders the reel, lays the master under it, and takes the stills from the film's own frames at rest:
  stories 01 the hook, 02 the story's peak open, 03 the ending; carousel 01 the hook, 02 to 09 eight months
  spread across the year in calendar order, the peak among them, 10 the ending. `build/frames/` holds the hook, a month,
  the peak and the closer at half size for the critics; `build/render/film-report.json` lists every failed job and
  every font or photograph that failed to load. The render draws the composition in a headless browser and
  encodes with ffmpeg; the film is the same on any machine.
- `preview` and `render` render the film in chunks kept under `build/render/chunks/`, then join them: on an NVIDIA
  card the film is one chunk, on the processor each chunk is 60 frames. When a render stops partway (a restart, a lost connection, a killed command), run the same command again: it keeps
  every chunk that is whole and renders only the rest. Never delete `build/render/chunks/`. Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is in
  `build/render/<name>.log` (`preview` or `film`); the command's line
  `render <name>: N chunks kept, M rendered, K to go` says where it stands, and the time per chunk so far times the
  chunks to go is the time left. A second render started in the same run while one runs exits at once and names the
  log of the one running.

The standards the film is held to are in `S/design/standards.md`. To change the film, change `taste.json` (the words)
or `picks.json` (a line, a scene) and run the steps again from `storyboard.py draft`, the vote included; never edit `film.json`, a board
or anything in `out/` by hand.

## Look before the critics do

Open every `build/frames/*.png`, the first and last carousel cards and the three stories with the Read tool, and cut a
12 frames a second strip of `out/film.mp4` (`ffmpeg -i out/film.mp4 -vf "fps=12,scale=-2:300,tile=12x3" s-%02d.png`)
and read it. Text cut off, type fading into what is under it, a month with no words on screen, a frame with nothing on it,
a hold over a second before the stop: fix the cause and render again now.
No cut round starts while one of these is still on screen or on a card: fix its cause and look at that passage or
card again first.
