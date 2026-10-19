# Step 8: deliver

```
python3 S/scripts/deliver.py
```

Writes `out/caption.md` (the caption paragraph and hashtags), `out/brief.md` (every assumption: the data found,
the year, the handle, how the top posts were ranked, what was left out, the critic's scores) and
`out/review.html` (plays the video, shows the ten cards and the caption with a copy button), then runs
`qa.py gate`. It exits 0 only when the gate passes.

A FAIL names what is wrong: fix that, rebuild the steps after it, and run `deliver.py` again. Never deliver past a
failed gate, and never loosen a check.

Reply to the person in a few plain sentences: what you made (the video, ten carousel cards, the caption), where
it is (`out/review.html` first), the two or three assumptions that matter most from `out/brief.md`, and that the
video has no sound so they can add one when they post. Nothing about scripts, steps or checks.
