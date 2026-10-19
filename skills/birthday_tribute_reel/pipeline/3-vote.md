# 3. Vote: a panel picks, with reasons

Goal: `build/vote.md` and `build/winner.json`.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the seven criteria). Then, as each critic in turn, open every
board's `sheet.png` and `storyboard.md` and fill in `build/vote/scores.json`: a whole number 1–5 for each criterion
on each board, and one paragraph per board (at least 25 words: what works, what fails, what you would change).
Score honestly; the three boards should not come out equal. The person's critic speaks in the first person from
`taste.md`, as the one sending the film to the named one.

```
python3 S/scripts/vote.py tally
```

The highest total wins; a tie goes to the person's critic. The runners-up stay on the review page so the person
can say "do the second one".

## "Do the second one"

When the person asks for a runner-up after delivery, run the rest of the pipeline from movement 5 with
`--board N` on `clips.py` and `storyboard.py snap`.
