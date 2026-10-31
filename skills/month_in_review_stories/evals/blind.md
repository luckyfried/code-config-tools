# Blind run

A fresh agent, one person's month, one request, no help. The run proves the kit triggers on a plain phrasing and
carries a cold agent from the request to a green gate, from nothing but the skill folder.

## Trigger phrasings

Any one of these, typed as the whole request:

- make my september recap stories
- my month in review
- october recap stories
- monthly wrap-up please, as stories
- what I posted this month as stories
- month recap

## The fixture

`S/evals/fixtures/september-recap/` is one person's own table, photographs and request:

- `posts.csv`: her eight posts of September 2026 (date, type photo or reel, caption, likes, comments, photo), a month
  with things in it: a first loaf, a first ride to the sea, her sister's wedding, a concert with a friend, a market
  morning, the last swim of summer with two friends, a month of mornings on the balcony;
- `photos/`: the photograph of each post;
- `pulled/items.json`: what an agent pulls from her connected account, the handle and the name and nothing else;
- `request.txt`: her request, which names the month, asks for the best bits of it and a caption, and says she
  writes in lowercase with no exclamation marks.

The handle on the cards comes from `items.json` and the month from the request; nothing in the kit carries either.

Every caption in `posts.csv` is written from its photograph (`photos/SOURCES.md` says what each one shows). A fixture
or a seed photo set whose captions say something its photographs do not show is fixed in its captions, never on a
board or in a composition.

`S/evals/fixtures/make_person.py SANDBOX` writes a second person through the export doors instead: an Instagram
export in the JSON layout with per-post insights and a small Facebook export.

## The run

The skill folder is copied alone into an empty workspace, as a user's machine has it, and the fixture beside it:

```
SANDBOX=/path/to/blind-with
mkdir -p "$SANDBOX/.claude/skills"
cp -r S "$SANDBOX/.claude/skills/month_in_review_stories"
cp -r S/evals/fixtures/september-recap/posts.csv S/evals/fixtures/september-recap/photos \
  S/evals/fixtures/september-recap/pulled "$SANDBOX/"
cd "$SANDBOX" && CSC_DISABLE_KEYCHAIN=1 claude -p "$(cat S/evals/fixtures/september-recap/request.txt)" \
  --dangerously-skip-permissions --setting-sources project,local --strict-mcp-config \
  --output-format stream-json --verbose > run.log 2>&1
```

`--setting-sources project,local` keeps the operator's own hooks and settings out; `--strict-mcp-config` with no
MCP config leaves the agent with no Instagram, browser or video tool. The agent passes `--pulled pulled` to
gather.py because the pulled folder is what it has from her account. The without-kit run is the same command in a
sandbox with the fixture and no `.claude/skills/`.

## Pass

The run ends with `out/film.mp4` (the reel), three or four cards in `out/cards/` (each `NN-story.mp4` and
`NN-story.png`), `out/caption.md` and `out/review.html`; `deliver.py`
printed `GATE GREEN`; `build/template.json` holds next month's look; and in the run's build folder (`build/<run stamp>/`)
`brief.md`, the storyboard's sheets
(`storyboards/drive/reel-sheet.png` and `sheet.png`), `vote.md`, `critic/timed.json`, the cut scores in `critic/`, `qa/check.json` and the strips
`timeline/film-strip.png` exist, and no `out/series.mp4` (her request does not ask for the cards as one video).
Every beat shows one of her moments, with her own caption under its photograph; no like, comment or post count is on
screen (her request asks for the best bits, never her numbers); and every word on screen and in the caption is
lowercase with no '!'.

## Judging

Every result, with and without the kit, is judged on the seven rules (R1 to R7) in `S/critic/critic.md` by eye,
against the bar of a mean of 4.5 with none under 4: the rest sheets, the strips, the reel, the series and the cards.
