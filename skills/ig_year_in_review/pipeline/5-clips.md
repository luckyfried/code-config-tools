# 5. Generated clips, placed inside the film

Goal: every clip the winning storyboard lists, made by your video model, conformed into the film; a clip that
does not arrive is replaced by an animated treatment of one of their photos, so no beat is ever missing.

```
python3 S/scripts/clips.py list
```

`list` prints one block per clip: its beat, its role (the opener's world, texture between chapters, a still of
theirs brought to life, the closer), the prompt built from `taste.json` (palette words, subject, mood, camera,
light, vertical 9:16, its length in seconds, "no text, no logos, no people's faces"), the photo to start from when
the clip is image-to-video, and the file to save.

## Generate

If you have a video generation tool, generate every clip the list names with exactly its prompt (and its photo,
when your model takes an image), at 9:16 and the length it says, and save each one as `build/clips/NN.mp4`
(`.mov` and `.webm` are read too). A clip whose role is "their own reel" is cut from their footage; do not
generate it. Generate them all before going on; a model that refuses one prompt can be asked once more with the
prompt simplified.

If you have no video generation tool, generate nothing and say so in the next command.

## Conform

```
python3 S/scripts/clips.py normalize [--why "no video model in this session"]
```

`normalize` scales and crops each file to 1080×1920, conforms it to 30 fps, trims or loops it to its beat, grades
it with the film's grade, and writes `build/public/clips/NN.mp4`, its frames as `build/public/clips/NN/0001.jpg`
onward (the renderer reads the frames, which retry on their own when a request drops), and `build/clips.json` (each
clip: generated, their_reel or substituted, and why). Pass `--why` when clips are missing for a reason you know; `brief.md` quotes it.
