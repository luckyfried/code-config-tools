# 0. Gather: use anything and everything you already have access to

Goal: a new run folder, `build/<stamp>/`, holding every photo, reel, story, caption, like, save, comment and follow
of theirs you can reach, in its `library/` and `library.json`. More sources are better. Nothing you can already reach is off limits.
The nine are picked from their own like and comment counts, so the counts per post matter most: a door that gives
posts without their likes is worth less than one that gives them.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the year: posts (caption, date, likes, comments, place, media),
   reels, stories and highlights, likes and saves (account, caption, the media when you can), the comments they
   wrote, followers and following, tagged photos, insights when present. Save the media files under
   a folder of your own (for example `pulled/` under the workspace) and write `items.json` beside them in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll the year, and save what you can the same way (posts with dates and
   captions, the images, the like and comment counts shown).
3. **A file of theirs that lists their posts with their numbers**: a `posts.json` in any shape, a `likes.csv`, a
   sheet, notes of how their posts did. The numbers are theirs, so they rank the nine: write every post it lists into
   `items.json` in the shape `gather.py --help` prints (`ts` from its date, `likes` and `comments` as the file gives
   them, its caption, `media` the path of its photograph relative to `items.json`, `handle` when the file names their
   account, and `source` naming the file, which gather.py records as the door) in a folder of your own, for example
   `pulled/`, and pass `--pulled pulled`.
   Copy nothing: point `media` at their photographs where they are. A number the file does not give stays out; never
   fill one in.
4. **A "Download your information" export** anywhere under the workspace (a folder, a `.zip`, or a folder holding
   its `posts_1.json` and media): gather.py finds it, with the counts its insights or its posts carry.
5. **Their photo folder**: the setting `BEST_NINE_PHOTOS`, or a folder they named in the request passed as
   `--photos DIR` (which wins). The nine's photographs are read from it by file name first, so a full-size copy of
   each post wins over the download's compressed one.
6. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled pulled] [--photos DIR] [--year YYYY]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. It prints `run: build/<stamp>`: every later command takes that folder as `--run`. `--year` only when the person named a year; otherwise it picks the latest year with enough posts.

## When every door is closed

gather.py exits 3 and writes the run's `brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a best nine from nothing.

## Done when

gather.py printed `run: build/<stamp>`, the run's `library.json` exists, and the summary names a year, their handle (or none, and then no handle is set anywhere) and counts. Read its `assumptions`; they
go into `brief.md` as they are. A year with fewer than nine posts is not an error: the run makes the film of the
posts there are.
