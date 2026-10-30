# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, story, caption, like, save, comment and follow of theirs you can reach, in the run's
`library/` and `library.json` (gather.py starts the run: `build/<run stamp>/`). More sources are better. Nothing you
can already reach is off limits.
The places come from the geotags first, then from the places named in captions, album and folder names, so the
location per post and story matters most: a door that gives posts without their places is worth less than one that
gives them.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the year: posts (caption, date, likes, comments, place with its
   name and coordinates, media), reels, stories and highlights (each with its location sticker or place), likes and saves (account, caption, the media when you can), the comments they
   wrote, followers and following, tagged photos, insights when present. Save the media files under
   `pulled/` in the workspace root and write `pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll the year, and save what you can the same way (posts with dates, captions
   and the place named above each post, the images, the like and comment counts shown).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR` (the GPS and the date in
   each photo's EXIF, the folder names such as `2026-05 Seville` and the file names such as `2026-05-17_fes.jpg`
   carry the places and the days).
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

A set of photographs of the places they hand over (a folder per place, each ranked best first by a `manifest.json`
beside the files) is not a door: movement 1 reads it with `research.py --set DIR`.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled pulled] [--photos DIR] [--year YYYY]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. `--year` only when the person named a year; otherwise it takes the latest year with at least 12
posts, reels and stories (this year, for anyone who posts).

## When every door is closed

gather.py exits 3 and writes the run's `brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a map from nothing.

## Done when

The run's `library.json` exists and gather.py's summary names a year, a handle (`none` when the data has no username: the film then shows the year alone, and nothing stands in for a handle) and counts. Read its `assumptions`; they
go into `brief.md` as they are.
