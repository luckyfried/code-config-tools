# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, story, caption, like, save, comment and follow of theirs you can reach, in
`build/library/` and `build/library.json`. More sources are better. Nothing you can already reach is off limits.
The brand is measured from their own posts (the palette from the pictures, the voice from the captions, the
cadence from the timestamps) and what they aspire to from what they like and save, so the posts with their
captions and dates matter most, and the liked images come next.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the last year: posts (caption, date and time, likes, comments,
   place, media), reels, stories, likes and saves (account, caption, the media when you can), the comments they
   wrote, followers and following. Save the media files under `build/library/pulled/` and write
   `build/library/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll the year, and save what you can the same way (posts with dates and
   captions, the images, the like and comment counts shown; the saved and liked posts when the page shows them).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR`.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.
6. **Liked or saved images** (screenshots, a moodboard): pass `--likes DIR`, or gather.py finds a folder named
   likes, liked, saved, inspiration or moodboard.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/library/pulled] [--photos DIR] [--likes DIR]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export, folder and likes doors itself and records them all in `library.json`;
`brief.md` lists them. It reads the last twelve months; `--since YYYY-MM-DD` only when the person named a start.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a brand kit from nothing.

## Done when

`build/library.json` exists and gather.py's summary names a handle, a window and counts. Read its `assumptions`;
they go into `brief.md` as they are.
