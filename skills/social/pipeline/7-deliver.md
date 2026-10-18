# Step 7: Deliver

```
python3 S/scripts/deliver.py
```

It re-runs the gate and writes `out/index.html`: the posting plan, each post with its
files, every caption with a Copy button, alt text, the idea, your assumptions, image
credits and the QA status. If it exits 1, the page carries a red "Not finished" banner:
fix what it lists, then run it again. Never finish with that banner on the page.

Open `out/index.html` once (read it, or screenshot it with Chromium) to confirm the
images load and the captions are there.

Before you finish, `out/` holds only what the user should get:
`index.html`, the post files (`pNN-...png/.mp4`), `copy.md`, `brief.md`, `brand.json`,
`credits.md` (if any CC images), `qa.json`. Your HTML designs, `design-system.css` and `design-notes.md` stay in `build/`. Frames, crops, downloads, overlays and data
JSON stay in `build/`. Delete stray files from `out/` (the gate lists any that aren't in a post).

Tick box 7.

## The final reply (short; the page has the detail)

```
Made: <n> posts for <platforms>: <one line on the idea>.
Files: out/index.html (open this), plus <list of the post files, grouped>.

Plan:
- <Day, date, time>: <platform>, <post> 
- ...

Assumptions (change any and I'll redo it):
- <3-6 that matter: dates, prices, platforms, stand-in photos, palette/fonts in brand.json>

Next time: drop photos in in/ and I'll use them instead of <type-only / stand-in images>.
```

No design lecture, no process recap, no list of the steps you ran, no questions.
