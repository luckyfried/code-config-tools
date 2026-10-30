# 0. Gather: use anything and everything you already have access to

Goal: every photo, reel, story, caption, comment and tag of theirs you can reach, and the named one's own feed
when you can reach it, in the run's `B/library/` and `B/library.json`. More sources are better. Nothing you can
already reach is off limits. What matters most here is what the two share: who is tagged in each post, who wrote
each comment, and the threads under the named one's posts.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull everything: posts (caption, date, place, media, the accounts
   tagged, the comment thread with who wrote each line), reels, stories and highlights, the comments they wrote,
   followers and following. Save the media files under `build/pulled/` and write
   `build/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile and save what you can the same way (posts with dates, captions, tags and
   comments, the images). Then open **the named one's profile** and save a dozen or more of their posts as
   `build/pulled/feed-<their handle>/items.json` with `"feed_of": "<their handle>"`, their captions, tags and
   comment threads: their colors, their humor and the photos they posted of the two come from there.
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`), or a posts file
   (a `.json` of `{"posts": [{"date", "media", "caption", "comments": [{"user", "text"}]}]}`): gather.py finds it,
   reads each post's comments as its thread, and leaves out a post with no date, saying so in one line.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR`.
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/pulled] [--feed DIR] [--photos DIR]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export, the named one's feed and the folder doors itself and records them all in
`library.json`; `brief.md` lists them. A feed folder anywhere under the workspace is found on its own; `--feed`
names one that is elsewhere. The whole history is kept, because a friendship spans years; `--year` only when the
person asked for one year.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. This run makes no film: tell
the person that, then exactly that sentence, and stop. Do not make a tribute from nothing.

## Done when

`B/library.json` exists and gather.py's summary names a handle, the counts and any feed it read. Read its
`assumptions`; they go into `brief.md` as they are.
