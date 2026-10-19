# 0. Gather: use anything and everything you already have access to

Goal: every photo, clip, story, caption, like, save, comment and follow of theirs you can reach, in
`build/library/` and `build/library.json`. More sources are better. Nothing you can already reach is off limits.
The trip is found from dates, geotags, captions, albums and folder names, so what matters most is that every
item keeps its date, its place or coordinates, its caption and the people tagged in it: a door that gives the
photos without their dates or places is worth less than one that keeps them.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull posts, reels and stories (caption, date, place or coordinates,
   people tagged, the track on it when shown, the media), albums, likes and saves, the comments they wrote,
   followers and following. Save the media under `build/library/pulled/` and write
   `build/library/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool signed in to Instagram or Facebook, open
   their profile and the trip's posts, and save what you can the same way (dates, captions, places, the images).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request (the trip's folder): pass it as `--photos DIR`.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/library/pulled] [--photos DIR]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. Every year is kept; the next movement picks the trip.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a trip film from nothing.

## Done when

`build/library.json` exists and gather.py's summary names a handle and counts (how many items carry coordinates).
Read its `assumptions`; they go into `brief.md` as they are.
