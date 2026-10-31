# 5. Produce: the clips, the music, the films, the posts and the grid after

Goal, in the run's `out/`: `film.mp4` (1080x1920, about 20 s: the hook, the nine posts, the closer),
`film-landscape.mp4` (1920x1080) and `film-square.mp4` (1080x1080), each re-placed for its frame and never centered,
each at 30 fps, H.264, AAC 192 kbps at -14 LUFS; `posts/NN.png` (1080x1350 each, laid out in the picked look's type and
colors, post 01 goes up first); `story.png` (1080x1920, the reel's closer as a Story); `caption.txt` (what to write
under the reel and under each post); and `grid-after.png` (their profile with the new posts in place over the real
grid). Beside `out/`, `frames/<format>-<rest>.png` holds the rendered films' settled frames at the hook, the densest
post and the closer, at the films' own size.

Everything here is made from the picked board (`board.json`). When the person picks another look later, run
`storyboard.py pick` with its letter and then every step of this page again, in the same run folder.

## Clips

```
python3 S/scripts/clips.py list
```

`list` writes `clips/requests.json` from the board: the hook's world (clip 00, from the plan's `film.world`), a still
brought to life on each post the frame holds and the texture between chapters on each post it passes (each from the
post's `shot`), each naming the camera move of its beat, its seconds and a seamless loop. Read every prompt it prints:
a prompt that does not read as a shot a cinematographer would ask for is fixed in the plan (`plan.py check`, then
`storyboard.py draft`, `sheets` and `pick` and the steps after it), never in the requests file. With a video model, generate each clip from the
photograph it names and save it where it says (`clips/NN.mp4`). Then:

```
python3 S/scripts/clips.py normalize --why "no video model in this session"
```

`normalize` conforms each clip that arrived and records the rest as stand-ins (`clips.json`); `--why` says, in plain
words, why the missing ones did not arrive, and leave it off when every clip arrived. A stand-in is the move the board
names for it on the still photograph: on a held post the crop forward of its own photograph, which recedes and dims
behind it, and on a passed post the card sliding or falling onto the wall; the light wraps every cut edge and every
floating card throws its shadow on the wall.

## Music

The music is theirs: the track they chose, else a bed composed for the picked look. `find` takes them in that order:

1. A track the person gave you or asked for: save it as `music/source.<ext>` in the run folder and run
   `music.py find --origin "<where it came from>"`.
2. Otherwise `find` runs `make`: a bed composed on real instruments from the picked look's own recipe (a quiet look
   gets felt piano and pads, a loud one drums and bass), at the board's tempo, unless their music brief (`taste.json`
   `music.styles`) names a sound they asked for. `music.json`'s origin says, in plain words, which recipe played, why,
   in what key and at what tempo.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
python3 S/scripts/music.py master
```

`analyze` reads a track they brought (its tempo, beat grid and downbeats); a composed bed needs no reading. `master`
lays the music on the cut's tempo from its first downbeat and puts the board's sound cues under it (`hit`, `riser`,
`impact`, `stop`, played in the recipe's own instruments, each where its beat lands), the effects `FX_UNDER_BED_LU` (8)
LU under the bed. It stops the music on the board's stop cue with the picture and brings the mix to -14 LUFS
integrated with a true peak under -1.5 dB. It prints both loudness numbers and writes them to `music.json` and to the
storyboard's `Mixed:` line (its `Music:` line takes the origin); the gate's audio row is red when the effects sit less
than 7 LU under.

## Render

```
python3 S/scripts/film.py render
```

`render` refuses a board that is not the one picked (`winner.json`) and runs the swap test, which `plan.py check`
already ran on the cells as planned, on the nine as placed (`critic/swap.json`). It renders the three films from the
one board in one browser; on a machine with an NVIDIA graphics card the frames are drawn and encoded on the card. It
lays the mastered music under each, writes the posts, the Story card, the caption file, the grid after and the frames
at the rests, and `render/film.json`. A font or image that failed and a failed job land in `render/film-report.json`.
A page whose graphics context was lost or whose shaders failed is an attempt the renderer runs again by itself; when a
job still fails, run the same command again and it resumes. `film.py preview` renders the reel at half size first when
you want a quick look at the cut (`preview/film-strip12.jpg`, twelve frames a second, one second to a row).

## A render that was stopped

`preview` and `render` draw every film in chunks saved in the run, under `render/chunks/` (60 frames each on a
machine without an NVIDIA card, the whole film in one on a machine with one), and join them once all of them are
whole. When a render is interrupted (the machine restarted, the session died, the browser
stopped), run the same command again: the finished chunks are kept and only the missing ones render, and the printout
says `render <name>: N chunks kept, M rendered, K to go`. Never start over and never delete `render/chunks/`; a changed
cut, photograph or kit renders into chunks of its own by itself. Only one render runs in a run at a time; a second
one exits and names the log of the one running.

Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Its progress is in `render/<name>.log`
(`render/preview.log`, `render/film.log`). Once the first chunks have landed, the seconds one chunk took times the
chunks still to go is the estimate to tell the person.

## Look before the critics do

Open every `out/posts/NN.png`, `out/story.png`, `out/grid-after.png` and every `frames/*.png` with the Read tool, and the reel at
twelve frames a second, one second to a row (`qa/film-strip12.jpg` from `qa.py check`). A frame where the ground is the stage instead of a photograph, a beat
that holds longer than its words need, a photo cropped past its subject, a word cut off, a closer naming the wrong
day: fix it in the plan, then `storyboard.py draft`, `sheets` and `pick` (the same letter), the music and the render
again.
