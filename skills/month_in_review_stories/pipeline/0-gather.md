# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, story, caption, like, save, comment and follow of theirs you can reach, in
`build/library/` and `build/library.json`. More sources are better. Nothing you can already reach is off limits.
The month is set against their year and the three that hit are picked from their own like and comment counts, so
dates and counts per post matter most: a door that gives posts without their likes is worth less than one that
gives them.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the month and the eleven months before it: posts (caption, date, likes, comments, place, media),
   reels, stories and highlights, likes and saves (account, caption, the media when you can), the comments they
   wrote, followers and following, tagged photos, insights when present. Save the media files under
   `build/library/pulled/` and write `build/library/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll back through the month and the year before it, and save what you can the same way (posts with dates and
   captions, the images, the like and comment counts shown).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR`.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/library/pulled] [--photos DIR] [--month M]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. `--month` only when the person named a month ("september", "2026-09", "last month", "this month");
otherwise it takes the last full calendar month, or the latest full month the data covers when that one is empty.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a month in review from nothing.

## Done when

`build/library.json` exists and gather.py's summary names the month, a handle and counts. Read its `assumptions`; they
go into `brief.md` as they are.
