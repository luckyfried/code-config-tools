# 3. Vote: a panel picks, with reasons

Goal: the run's `vote.md` and `winner.json`.

```
python3 S/scripts/vote.py ballot --run build/<stamp>
```

Read `S/critic/critic.md` (the three critics, the seven criteria and the swap test). Then, as each critic in turn,
open the storyboard's `sheet.png` and `storyboard.md` and fill in the run's `vote/scores.json`: a whole number 1 to 5
for each criterion on each board, and one paragraph per board (at least 25 words: what works, what fails, what you
would change). As the motion designer, also fill in `swap`: for each board's hook, densest beat and closer, whether
the composition passes the swap test and why, in a sentence. Score honestly. The person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally --run build/<stamp>
```

The board wins when it passes the swap test on all three compositions. A board that fails the swap test anywhere
cannot win: change the tone builder's layout for those posts and draft again.
