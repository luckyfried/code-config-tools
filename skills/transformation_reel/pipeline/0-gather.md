# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, caption, like and save of theirs you can reach, in `RUN/library/` and `RUN/library.json`.
A transformation runs from the subject's first post to its latest, so every dated post matters, whatever its year:
the oldest ones most of all. More sources are better. Nothing you can already reach is off limits.

`gather.py` starts the run: it makes `build/<run stamp>/`, names it in `build/RUN`, and every later movement reads
and writes there.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull everything you can, as far back as it goes: posts and reels
   (caption, date, media), stories and highlights, likes and saves (account, caption, the media when you can).
   Save the media files under `build/pulled/` and write `build/pulled/items.json` in the shape `gather.py --help`
   prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll back to the oldest posts of the subject, and save what you can the same way
   (posts with dates and captions, the images).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR`. Each photo is dated by its
   EXIF, else by a date in its file name (`2026-05-16.jpg`), and captioned from a `captions.csv` (a header naming
   `caption` and `file` or `date`) or `captions.json` kept beside the photos.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

Beside the doors: a folder of progress posts they liked or saved (named liked, likes, saved or inspo, or passed as
`--likes DIR`). gather.py finds it; research reads the style of the before-and-afters they like from it.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/pulled] [--photos DIR] [--likes DIR]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export, folder and liked-folder doors itself and records them all in
`library.json`; `brief.md` lists them.

## When every door is closed

gather.py exits 3 and writes `RUN/out/brief.md` with one sentence on how to open a door. Tell the person exactly
that sentence and stop. Do not make a before and after from nothing.

## Done when

`RUN/library.json` exists and gather.py's summary names a handle, a date range and counts. Read its
`assumptions`; they go into `brief.md` as they are.
