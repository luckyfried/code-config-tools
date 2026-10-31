# 5. Clips: the photographs brought to life

Goal: `clips.json` in the run's folder, accounting for every clip `film.json` lists. Run it after `storyboard.py
snap` and before `film.py render`.

The film lists one clip per photograph, over the stretch the camera walks it: on the first photograph the hook's
world, the place the trip opens on; on every other the photograph brought to life; or, where the stop is shown by a
clip they shot on the trip, that clip (its role is "their own clip" and it needs no generation). One more, the texture
between chapters, is a close, held detail of the print the trip's longest leg leaves, which plays on that print while
the leg is drawn. Each request names a camera move read from its photograph, never the move of the request before it.

```
python3 S/scripts/clips.py list
```

`list` writes `clips/requests.json` and prints one block per clip: its span, its role, its length, the size of its
photograph, the photograph to start from, the prompt, and the file to save.

## Generate

If you have a video generation tool, generate every clip the list names from its photograph with exactly its
prompt, at the photograph's own shape and the length it says, and save each one as `clips/NN.mp4` (`.mov`, `.webm`
and `.m4v` are read too). A clip whose role is "their own clip" is cut from the footage they shot; do not generate
it. A model that refuses one prompt can be asked once more with the prompt simplified. With no video generation
tool, generate nothing and say so in the next command.

## Conform

```
python3 S/scripts/clips.py normalize [--why "no video model in this session"]
```

`normalize` scales and crops each file to its photograph's own size, so the film plays it on the card exactly where
the photograph was, conforms it to 30 fps, trims it to its stretch (looping a short file), grades it like the photographs and matches it the way its photograph was matched, and
writes its frames as `public/clips/NN-<digest>/0001.jpg` onward. A clip that did not arrive stands
in: the camera walks the still photograph in its layered move, and the texture's print lies still under the leg. `clips.json` records every clip as generated, their_reel or
stand-in; pass `--why` when clips are missing for a reason you know, and `brief.md` quotes it.
