# 3. Pick: the person picks a look, or the panel scores the three

Goal: `winner.json`, carrying the board the film is made from.

## The person picks

Show the person `out/boards.png` (each look's hook, a middle beat and its closer, with its name and one sentence)
and ask one question: which look do they want, the first, the second or the third. Their answer is the vote:

```
python3 S/scripts/vote.py pick --board N
```

Where the agent cannot ask (`taste.json` `ask` is false, or the session has no person to answer), pick the look their
taste points to and say why in one line, which `brief.md` and the review page carry:

```
python3 S/scripts/vote.py pick --board N --why "their feed is quiet film photographs, so the letterbox look"
```

Later, when they say "make the second one" (or the third), run the same `pick --board N` in the same run: every piece
made from the last look (its music, the cut, the critics' rounds and the film) goes, and the film is made again from
movement 4 in that look, from the same photographs and words.

## Or the panel scores them

When the person asks for the panel's view, or to compare the looks, run the ballot:

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics, the seven criteria and the swap test). Then, as each critic in turn,
open every board's `sheet.png` and `storyboard.md` and fill in `vote/scores.json`: a whole number 1-5 for each
criterion, one paragraph per board (at least 25 words: what works, what fails, what you would change), and the swap
test (`swap`: `pass` true or false and a `why` of at least eight words naming the frames). Score honestly. The
person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

The highest total among the boards no critic fails on the swap test wins. When every board fails it, there is no
winner: tally exits 1, and the boards are changed (`2-storyboards.md`) before the vote is run again.
