# Step 0: find their data

```
python3 S/scripts/setup.py
mkdir -p out build
python3 S/scripts/data.py
```

`data.py` looks for Instagram's own download ("Download your information", JSON) anywhere under the workspace,
by shape: a folder or a `.zip` holding `your_instagram_activity/` (or `content/posts_1.json`) and `media/`. It
reads posts, reels, stories, liked posts, comments, followers and post insights, tolerates any of them being
missing, repairs Instagram's broken accents and emoji, and writes `build/data.json` with every assumption it made.

- Several exports: it takes the newest and says so. Pass `--export <path>` only when the person named one.
- No export: it uses the folder of photos the person named (`--photos <dir>`), else the largest folder of
  photos under the workspace, and says so. The video then leaves out the chapters the photos cannot fill.
- Neither: it writes `out/brief.md` with the one sentence on how to download the data and exits 3. Reply with
  that sentence and stop; this is the only case without a video.
- The year is the latest year with real activity; pass `--year 2026` only when the person named a year.

Never ask for a login, a password, a link or an account name, and never fetch anything from Instagram. The
download is the only source.
