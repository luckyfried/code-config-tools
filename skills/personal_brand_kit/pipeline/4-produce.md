# 4. Produce: the music, then the timed cut

Goal: `proof-cut.mp4` in the run folder, the half-size proof of the picked look's reel cut to the music with the
music under it, with its strips (`cut-strip.png` at one frame a second, `cut-strip12.jpg` at twelve, a row a second)
and `cut.json`. Every critic round before the full-size cut measures and watches the proof (movement 5); once the
critics ship it, `film.py cut` makes the same cut at full size, `cut.mp4` (1080×1920, 30 fps; the reel delivered is
this file), and the film, with what else the person asked for, is rendered from it (movement 6).

## Music

The music is theirs: the track they chose, else a bed made here for the look they picked.

1. A track the person gave you or asked for: save it as `music/source.<ext>` in the run folder and run
   `music.py find --origin "<where it came from>"`, then `music.py analyze` (its tempo, beats and downbeats).
2. Otherwise `find` composes the bed: the picked look's own music recipe (`music` in its style card), unless the
   words in `taste.json` `music.words` name another ("soft piano"); `music.avoid` takes out what they never want.
   Its key comes from their feed's leading color and its tempo from the look's board. `music.json` says where the
   bed came from and why ("chosen by the look", "chosen by their words").

```
python3 S/scripts/music.py find
```

## Cut to the music

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/film.py cut --proof
```

- `snap` cuts the picked look (`winner.json`) and refuses with no pick. It retimes the look onto the music's grid:
  of the music's tempo, half it and twice it, the one nearest the look's own that keeps the film's length in range;
  when none does, the film keeps the look's tempo and `film.json` says why. It writes the three boards again at that
  tempo and `film.json` (the tempo, the length, where the music starts, the cuts, the rests, the boards).
- `master` starts the music on its first downbeat and lays the shared effects under it (`S/scripts/sfx.py`): a
  whoosh on every cut, a shutter where a photograph lands, an impact where a title or a slammed word lands, a riser
  into the closer and its impact, all in the bed's key and on its quarter-beat grid from frame 0, the effects
  `FX_UNDER_BED_LU` (8) LU under the bed; on a look whose cuts are hard it stops the bed on the board's stop cue, and
  on the others the music fades over the last bar. It writes the music's energy for every frame to
  `music/energy.json`. It brings the music to −14 LUFS integrated by one gain and writes it in 32-bit float; the
  film's mux masters the music and the effects together to −14 LUFS, once. It writes both loudness numbers to
  `music.json` and to `storyboard.md`'s `Mixed:` line; the gate's audio row is red when the effects sit less than 8 LU
  under.
- `cut` renders the reel through the kit's film composition (`S/motion/`, on the graphics card when there is one),
  lays the master under it, measures it, and writes the strips and `cut.json`. With `--proof` it renders the reel at
  half size as `proof-cut.mp4` and never writes over `cut.mp4` or anything in `out/`;
  `qa.py check` and `vote.py cut` read the proof while it is the newest cut, and every size they report is in board
  units, the same numbers the full-size cut gives. Without `--proof` it makes `cut.mp4` at full size and takes the
  proof away. Mastering again after the cut means cutting again: `film.py render` refuses a cut that carries another
  master, and a proof.

Every film renders in chunks saved in the run, `render/chunks/<name>/`, and is put together from them only when every
chunk is whole. When a render is interrupted (the machine restarted, the session died), run the same command again:
the finished chunks are kept, only the missing ones render, and the line `render cut: N chunks kept, M rendered, K to
go` says how far it got. Never start over and never delete `render/chunks/`; a changed cut gets chunks of its own by
itself. Run the cut and the render each in the foreground in one tool call with a 40-minute timeout on that call;
never start either in the background. Its progress is in `render/proof.log` (`render/cut.log`, `render/film.log`); once the first chunks
land, their time times the chunks still to go is the estimate to give the person. One render runs in a run at a time:
a second one exits and names the log of the one running.

Open `cut-strip.png` with the Read tool before anything else reads the cut.

To change the film, change its source (the words or the moments in `taste.json`, the cast, the music) and run
`storyboard.py draft`, `check`, `sheets`, the pick, `music.py find`, `snap`, `music.py master` and `film.py cut
--proof` again; never edit a board or `film.json` by hand.
