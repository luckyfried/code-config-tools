# 0. Gather: the launch, then anything and everything you already have access to

Goal: the launch as the person gave it (the product, the date, where its assets are), every photo, reel, story,
caption, like, save, comment and follow of theirs you can reach, and the product's own stills and clips, all in
`build/library/` and `build/library.json`. More sources are better. Nothing you can already reach is off limits.
The hooks are ranked by their audience's response, so the comment and save counts per post matter most: a door that
gives posts without their counts is worth less than one that gives them.

## The launch, from the request

Take three things from what the person wrote, in their words:

- **the product** (or drop, or event): its name as they wrote it;
- **the date**: as they wrote it ("November 14", "2026-11-14", "next Friday" written out as a date);
- **the assets**: the folder in the workspace or the link they named. A link is passed as it is; gather.py
  downloads the page's images.

Whatever they did not name, leave out: gather.py infers it (the name from the posts that repeat it, a folder named
like the product, else their own posts about it) and lists the inference as an assumption in `brief.md`.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the year: posts (caption, date, likes, comments, saves, place,
   media), reels, stories and highlights, likes and saves, the comments they wrote, followers and following,
   insights when present. Save the media files under `build/library/pulled/` and write
   `build/library/pulled/items.json` in the shape `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll the year, and save what you can the same way (posts with dates and
   captions, the images, the counts shown).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--photos DIR` (the product's asset folder
   goes in `--assets`, never here).
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --product '<name>' --date '<date as written>' --assets '<folder or link>' \
  --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled build/library/pulled] [--photos DIR] [--year YYYY]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. `--year` only when the person named a year; otherwise it reads the 365 days ending at the latest post.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a launch film from nothing.

## Done when

`build/library.json` exists with its `launch` block (product, date, assets) and gather.py's summary names a handle,
counts, the product's stills and clips. Read its `assumptions`; they go into `brief.md` as they are.
