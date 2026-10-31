# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, story, caption, like, save, comment and follow of theirs you can reach, in
the run's `library/` and `library.json`. More sources are better. Nothing you can already reach is off limits.
The grid is their last 30 posts in posting order, and the audit reads their likes and saves per post, so a door
that gives the posts with their counts matters most. The next nine are made from everything else: carousel slides,
stories, Facebook photos, the photo folder. More of those means better posts.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull their profile (handle, name, bio, follower and following counts)
   and the last year: posts with every carousel slide (caption, date, likes, comments, saves, place, media),
   reels, stories and highlights, likes and saves (account, caption, the media when you can), the comments they
   wrote, followers and following, tagged photos, insights when present. Save the media files under
   `build/pulled/` in the workspace root and write `build/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, read the bio, scroll at least the last 30 posts, and save what you can the same
   way (posts in order with dates and captions, every carousel slide, the like and comment counts shown).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR`. When you know whose
   photos they are, write their handle, name and bio into `build/pulled/items.json` (no posts needed). A folder with
   no feed export is the pool the next posts are made from and the grid is empty; the handle, the header and the
   closer are theirs, and with no profile the handle is `@you`.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/pulled] [--photos DIR]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a grid from nothing.

## Done when

`library.json` exists in the run folder gather.py started and gather.py's summary names a handle, the grid's 30 posts (when there is a feed) and the library's counts. Read its `assumptions`; they
go into `brief.md` as they are.
