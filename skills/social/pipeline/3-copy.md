# Step 3: Copy

Captions that sound like the person behind the counter, in the exact structure
`deliver.py` reads. Then lint them with `qa.py copy`.

## Hard rules

1. **Hook before the cutoff.** The first line carries the point (the offer, the news, the
   joke). Visible before "more": Instagram ~125 characters, TikTok ~150, LinkedIn ~210,
   Facebook ~120 on mobile, Pinterest ~50. Never open with the business name, "Happy
   Tuesday!", "Exciting news!" or a hashtag.
2. **Offer terms once.** Price, dates, limits and fine print appear once per caption, in
   plain words. The full terms block (end date, time zone, exclusions) appears only in
   the launch caption and the last-call caption. Other captions refer back ("the $2
   tacos", "before Friday").
3. **Compute every date and weekday** with a command (see `0-scope.md`). Never type a
   weekday from memory. `qa.py copy` checks every "Tuesday, October 20"-style pair.
4. **No invented facts.** No addresses, hours, years, awards, reviews, ingredients,
   "family recipe", "best in town" or statistics that were not given. If a fact would help,
   write `[address]` or `[hours]` in the caption and list it in Assumptions.
5. **Real CTAs only.** Say what to do and where: "come hungry", "link in bio", "DM us
   CAKE", "tap the link sticker", "call [phone]". The image never carries a button.
6. **Hashtags, counted.** Instagram 3-5, TikTok 3-5, Facebook 0-2, X 0-1, LinkedIn 0-3
   at the end, Pinterest 0 (use keywords in the sentence). Prefer local + niche
   (`#sacramentobakery`, `#tacotuesday`) over huge generic tags. Never invent a city tag
   if the city wasn't given.
7. **Keep the jokes.** When a rule below hits a joke, rewrite it into a plain sentence
   that is still funny. Do not delete it or flatten it into a fact.
8. **One voice.** Use `brand.json` voice. Read two captions in a row aloud: if they open
   the same way, rewrite one.

## No AI tells (never write these)

- **Contrast reveals**: "It's not X, it's Y." "Not because X. Because Y." State Y directly.
- **Negation lists**: "No X, no Y, no Z." Say what does happen. One plain absence is fine.
- **Self-answered questions and colon reveals**: "The result? Pure joy." "The best part: it's $2."
- **Trailing pile-ons**: a full claim, then a comma and more restating clauses.
- **Stock phrases**: "Say goodbye to", "X, reimagined", "Unlock", "Elevate", "Take it to the next level", "Here's the thing", "game-changer", "look no further", "indulge", "treat yourself", "mouthwatering", "delectable", "nestled", "boasts", "whether you're X or Y".
- **Em dashes** in captions. Use a full stop, comma or line break.
- **Broetry**: one short sentence per line for the whole post.
- **Engagement bait**: "Agree?", "Thoughts?", "Tag a friend who...", "Let that sink in", "Read that again". A real question you want answered is fine.
- **Emoji as bullets** (every line starting with an emoji). One or two emoji in a caption, used like a person would, is fine.
- **Hook slop**: generic "POV:", "Stop scrolling", "Here's what nobody tells you".
- **CTA slop**: "Don't miss out!", "Get yours today!", "Join thousands of happy customers".
- **Stacked fragments**: "Fresh. Fast. Delicious." Keep fragments and lists of three to one per post.
- **Manufactured feelings**: "We're so excited to announce", "I'll be honest...".

## Platform notes

- **Instagram feed**: hook line, 1-3 short paragraphs, CTA, hashtags last.
- **Instagram/Facebook Story**: no caption; write the on-image text (in the plan) plus the sticker to add: link, poll, countdown, question. Say which, and where (the empty band your design left).
- **Facebook**: shorter, conversational, links allowed in the body.
- **LinkedIn**: first-person, a real observation or story with a specific detail, line breaks where a person pauses, no hashtag wall, no "I'm humbled".
- **X**: one sentence that stands alone; link in a reply if reach matters.
- **TikTok/Reels caption**: one line plus 3-5 tags; the hook lives in the video's first second.
- **Pinterest**: title (keywords, under 100 chars) + description of 1-3 natural sentences with search words; link to the product/shop.

## out/copy.md structure (deliver.py parses this; keep the headings exactly)

```
# Copy: Taqueria El Sol

## Posting plan
| # | Date | Day | Time | Platform | Post | Files |
|---|---|---|---|---|---|---|
| 1 | 2026-10-20 | Tuesday | 10:30 | Instagram + Facebook feed | $2 tacos | p01-tacotuesday-1080x1350.png |
| 1 | 2026-10-20 | Tuesday | 11:30 | Instagram Story | $2 tacos story | p01-tacotuesday-story-1080x1920.mp4 |

## Post 1: $2 Taco Tuesday
Files: p01-tacotuesday-1080x1350.png, p01-tacotuesday-story-1080x1920.png, p01-tacotuesday-story-1080x1920.mp4
Alt: p01-tacotuesday-1080x1350.png | Poster in red and yellow reading "$2 tacos, every Tuesday, all day".
Alt: p01-tacotuesday-story-1080x1920.png | ...
Story sticker: link sticker to [menu or map link] in the cream band under the headline.

### Instagram
$2 tacos. All day, every Tuesday. ...

#tacotuesday #tacos #[city]tacos

### Facebook
...
```

- `## Post N: title`, then `Files:` (comma-separated, file names in `out/`), one `Alt:` line per image (`file | text`), then one `### Platform` section per caption.
- Times are local, chosen from the playbook's rhythm. The Day column comes from a command.
- Alt text describes what the image actually shows (from the plan's "image shows" column, corrected after you see the render), including any words on it.

## Lint, then fix until clean

```
python3 S/scripts/qa.py copy
```

It flags em dashes, banned phrases, hashtag counts over the cap, weekday/date mismatches,
an offer term repeated in more than 3 places, a hook that runs past the cutoff, captions
that open the same way, missing `Files:`/`Alt:` lines, and a CC BY image in `credits.md` whose creator no caption credits. Fix every ERROR; read every
WARN and fix it unless you can say why it's fine. Tick box 3.
