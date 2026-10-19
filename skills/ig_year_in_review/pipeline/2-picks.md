# Step 2: pick the photos

```
python3 S/scripts/picks.py
```

Scores every photo (sharpness of color, contrast, exposure), finds where its subject sits so crops keep it,
converts HEIC and rotates by EXIF, and writes 1600 px copies to `build/photos/` plus `build/picks.json`: the
photos for each chapter (the three top posts, twelve from the busiest month, three from the quietest, fifteen
spread across the year for the numbers, one each for opener, people, loved, closer, cover and share; no photo
used twice where another good one exists).

Open `build/picks.json` and look at the opener and closer photos. A different photo for a chapter goes in
`build/story.json` as `"photo"` in step 3, never by editing picks.json.
