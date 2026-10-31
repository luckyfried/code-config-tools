# 0. Gather: use anything and everything you already have access to

Goal: every post, reel and story of theirs you can reach from the month, with its date, its caption, its photograph,
the people it tags and the place it names, in the run's `library.json`. The month is told by what happened in it, in
their own words, so the captions and the photographs matter most: a door that gives posts without their captions is
worth less than one that gives them.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool (an MCP server, a
   connector, an API you are signed in to), pull the month: posts and reels (caption, date, place, the photograph),
   stories, the handle (their Instagram username, never an email address or anything cut from one) and name. Write them to a folder
   (for example `pulled/`) as `items.json` in the shape `gather.py --help` prints, media files beside it.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll back through the month, and save what you can the same way (posts with
   their dates, captions, places and photographs).
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A table of their posts** anywhere under the workspace, as CSV: a posts table (date, type, caption, place,
   photo). gather.py finds it.
5. **Their own notes of what they posted** (a text file, a draft, a list in their message) when no door above
   gives the month: write the notes as a posts table, `posts.csv` in the workspace, one row per post with its date
   (the year the month last began when the note gives none), its type (a video is a reel), its caption and its likes
   exactly as the note says them, and nothing the note does not say. gather.py then finds it as the table above.

## Run

```
python3 S/scripts/gather.py --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled pulled] [--month M]
```

Every run of gather starts a new build folder, `build/<UTC stamp>/`, named in `build/latest`; every later step
reads and writes that folder. Name every door you tried with `--door`, open or closed, in plain words ("closed: no
Instagram tool in this session"). gather.py adds the export and table doors itself and records them all in
`library.json`; `brief.md` lists them. `--month` only when the person named a month ("september", "2026-09", "last
month", "this month"); otherwise it takes the last full calendar month, or the latest full month the data covers
when that one is empty.

## When every door is closed

gather.py exits 3 and writes `brief.md` in the run with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a month in review from nothing.

## Done when

The run's `library.json` exists and gather.py's summary names the month, the handle (or "none": with no username in
the data the cards carry no handle line) and what each door gave. Read its
`assumptions`; they go into `brief.md` as they are.
