# 3. The look: theirs, or picked by taste

Goal: the run's `winner.json`, the look the film is made in.

**When you may ask** (`taste.json` `ask` is `true`): show them `out/boards.png` and ask one question, "Which look do you
want: A, B or C?" Their answer is the look:

```
python3 S/scripts/vote.py pick --run build/<stamp> --board B
```

`--board` takes the letter, the number, the look's name or its style id.

**When nothing may be asked** (`ask` is `false`): pick the look by `taste.md` (their colors, their voice, what they
post, what to avoid), and give the reason in one line:

```
python3 S/scripts/vote.py pick --run build/<stamp> --board C --why "their year is dusk light and long tables; the letterbox holds it"
```

**When they ask you to choose for them**, the panel does: `vote.py ballot`, then as each critic in `S/critic/critic.md`
fill in `vote/scores.json` (a whole number 1 to 5 for each criterion on each look, a paragraph per look, and the swap
test on each look's hook, middle beat and closer), then `vote.py tally`. The highest total that passes the swap test
is the look.

A pick takes away everything made for an earlier look in the run (the cut, the music made for it, the preview, the
reads and the critics' rounds), so the steps from the music on run again for the look picked. A track they gave stays.
