# Step 1: the numbers

```
python3 S/scripts/stats.py
```

Writes `build/stats.json`: counts (posts, reels, stories, likes given, comments written, new followers), the top
three posts (by likes then comments when the export has post insights; by comments received otherwise; the best
photos spread across the year when neither exists, and `top_ranked_by` says which), months with the busiest and
the quietest, people (accounts commented on plus accounts tagged), loved (accounts liked most), and `register`
(how they write: lowercase share, emoji per caption, average words, their hashtags, sample captions).

Every number that appears anywhere later comes from this file. Never type a number from memory or round one up.
