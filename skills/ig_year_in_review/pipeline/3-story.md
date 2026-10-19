# Step 3: the words, in their voice

```
python3 S/scripts/cards.py draft
```

That writes `build/story.json`, a correct but plain draft from the numbers. Now rewrite it so it sounds like them.
Read `register` in `build/stats.json` first: if they write in lowercase, every line is lowercase; if they use
emoji, use their emoji in the caption (never on the cards); match their sentence length.

Per chapter (`opener numbers top months people loved palette closer`, plus `cover` and `share`):

- `kicker`: the small label, 30 characters at most ("your top three", "busiest month").
- `headline`: the big words, 34 characters at most, one idea, readable in two seconds. Never repeat the data the
  card already shows (the months card already shows the month's name; the numbers card already shows the counts).
- `line`: the burned-in caption for that chapter, 64 characters at most, a short sentence that adds something
  the card does not say. Every video chapter needs one.
- `months.quiet`: the headline over the quietest month.
- `closer.headline` says "see you in <next year>" in their voice; `share` invites people to make their own.
- `caption`: one paragraph, two to four sentences, in their register, about their year (not about the video).
- `hashtags`: 3 to 10; start from `register.top_hashtags`, add `#<year>wrapped` or `#yearinreview`.

Rules: every number you write must be one in `build/stats.json`; every @account must be theirs or one in
`people` or `loved`; no placeholder text. Delete the `"drafted": true` line when you are done.

```
python3 S/scripts/qa.py story
```

Fix every FAIL it prints and run it again until it says PASS.

Example of a chapter in a lowercase, emoji-light register:

```json
"months": {"kicker": "busiest month", "headline": "summer had me posting", "quiet": "february, hibernating",
           "line": "26 posts in july and only 3 in february"}
```
