# Step 4: palette and cards

```
python3 S/scripts/palette.py
python3 S/scripts/cards.py build
```

`palette.py` measures the colors across the year's photos, keeps the five that are most present and most
distinct, names them plainly (cream, sea blue, terracotta), and picks the card roles from them: a dark background
from their own darkest hue, the most vivid of their colors as the accent (lifted until it reads on the
background). `--accent '#RRGGBB'` overrides the accent with another of their colors.

`cards.py build` writes one template family for every card: Archivo Black headlines, Archivo labels, Inter text,
their photos behind every card with a light scrim, the kicker, headline and data in the same places on every
card. The video chapters (1080x1920) are written as two layers (photos, words); the ten carousel cards
(1080x1350: cover, the eight chapters, "share yours") as one. It writes `build/plan.json` (the render jobs) and
`build/cuts.json` (the video timeline, 45-60 s, each chapter 4-8 s; the top posts and the months chapters are
split into beats). Chapters with no data (no comments, no likes) are left out and the rest run longer.

Do not write your own HTML. A change to the cards is a change to `build/story.json` or the accent.
