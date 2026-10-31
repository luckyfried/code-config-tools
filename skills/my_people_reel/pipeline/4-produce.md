# 4. The timed cut: the storyboard on the music

Goal: `R/render/cut.mp4`, the storyboard timed to the music in 9:16 with the mastered music under it, and
what the critics read it by: `R/frames/film-strip.jpg` (12 fps), `R/frames/NN-<beat>.png` (each beat at rest),
`R/frames/cues/` (the frames around each sound cue over the waveform of the film's sound) and `R/clips/requests.json`
(the shots the film asks a video model for).
The film (and any other format the person asked for) renders only after the cut passes movement 5.

## Music

The music is theirs: the track they chose, else a bed composed for the picked look. `find` takes them in that order:

1. A track the person gave you or asked for: save it as `R/music/source.<ext>` and run
   `music.py find --origin "<where it came from>"`.
2. Otherwise `find` runs `make`, which composes the bed on real instruments from the picked look's own recipe (the
   card's `music`): its key from the palette's leading color, its tempo from the brief's (`R/taste.json` `music`),
   else the middle of the recipe's range, its sections turning where the board lands its impacts. The brief's
   `styles` words can name another recipe and its `avoid` words take out an instrument, the drums or a groove.
   `music.json`'s origin says which recipe and why.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds the onsets, the tempo, the beat grid and the downbeats.

## Cut to the music, master, render the cut

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/film.py cut
```

- `snap` cuts the picked board (`R/winner.json`) and refuses with no pick. It sets the board on the
  music's tempo (halved or doubled to the one nearest the board's own) from its first downbeat, and writes `R/film.json`,
  so every cut lands on the grid.
- `master` trims the music to the film from that downbeat (`R/music/bed.wav`), lays the board's sound cues under it
  (`R/music/fx.wav`, played in the recipe's own instruments: a hit as the camera lands on the hook, a hit as each
  person's stamp lands, the build into the wall and its impact as the wall settles, the hit as the tag lands on the
  last face, and the stop), the effects scaled by
  loudness to `FX_UNDER_BED_LU` (8) LU under the bed, and brings the mix to -14 LUFS integrated, true peak -1.5 dB.
  It prints both loudness numbers and writes them to `R/music.json`, and writes `storyboard.md` again with them and
  with the film's length and tempo; the check's audio row is red when the effects sit less than 7 LU under.
- `cut` lays the board out in 9:16 at the film's tempo, renders it through the kit's built composition
  (`S/motion/dist/`, drawn in Chromium with no window; on the graphics card when the machine has one), lays the music under it, and writes the strip and the beats at
  rest and the cue tiles. A board that has not changed since the last cut is not rendered again; `--again` runs the render anyway. The
  renderer tries a job again when the card's context is lost or a shader fails to compile, and a film that still
  comes back with white frames fails the command, naming its white seconds.

## The clips

```
python3 S/scripts/clips.py list
```

`list` writes `R/clips/requests.json`: one shot per clip the board asks for (the hook's photograph as the world the
film opens in, and each person's photograph brought to life), each naming its subject, the camera's move, the lens, the light read
from the photograph, its length and a seamless loop, no two in a row moving the camera the same way, with the photograph to make it from and the file to save it as. When this
session has an image-to-video model, make each clip from its photograph with its prompt and save it where the request
says. Then:

```
python3 S/scripts/clips.py normalize --why "<why any clip did not arrive, for example: no video model in this session>"
```

`normalize` conforms what arrived and records the rest as stand-ins in `R/clips.json`; a clip that did not arrive
stands in as the card's own layered move. When any clip arrived, run `film.py cut` again so the cut carries it.

## A render renders in chunks and resumes

`film.py cut` and `film.py render` render every film in chunks (60 frames each on a machine without an NVIDIA card,
the whole film at once on one with one), each saved in `R/render/chunks/` as it finishes. When a render is interrupted (the machine restarted, the session died, the command was stopped), run the
same command again: the finished chunks are kept and only the missing ones render. Never start over and never delete
`R/render/chunks/`; a changed cut renders into chunks of its own.

Run the cut and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Its progress is in `R/render/cut.log` (or
`R/render/final.log`): every chunk logs its progress and its time, and the command's last lines say how many chunks
were kept, rendered and still to go. Once the first chunks land, a chunk's time multiplied by the chunks still to go
is the estimate to give the person.

The standards the film is held to are in `S/motion/system/standards.md`. To change the film, edit the picked look's
`R/storyboards/<style>/storyboard.json` (order, lengths, which of their own lines) or `R/cast.json`, then run `check`, `snap` and `cut`
again; never edit `R/film.json` by hand.

## Look before the critics do

Open `R/frames/film-strip.jpg` and every `R/frames/NN-*.png` with the Read tool. A face cut by its crop, a line
hard to read, a beat that looks unfinished: fix it in the storyboard or the cast and cut again now.
