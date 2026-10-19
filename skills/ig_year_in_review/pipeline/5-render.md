# Step 5: render the cards

```
python3 S/scripts/render.py --batch build/plan.json
```

Renders every card and layer in one browser session (about 10 s), with the bundled fonts and the palette. It
refuses (FAIL, no file) a card whose words leave the safe area (clear of the Reels interface and the caption
band), words that cannot fit their box even after shrinking, an unfilled slot, or anything loaded from the
network. A FAIL names the card and the words: shorten those words in `build/story.json`, run `cards.py build`,
and render again. Every file it writes is fingerprinted in `build/render-report.json`.

Then open two of the carousel cards full size (`out/*-carousel-01.png` and `-04.png`) and look at them.
