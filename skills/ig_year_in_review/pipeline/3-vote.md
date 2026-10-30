# 3. The pick: a panel scores the three looks, then the person picks one

Goal: `build/vote.md` and `build/winner.json`.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics, the seven criteria and the swap test). Then, as each critic in turn,
open every `build/storyboards/<style>/sheet.png` and `storyboard.md` and fill in `build/vote/scores.json`: a whole
number 1 to 5 for each criterion on each board, and one paragraph each (at least 25 words: what works, what fails,
what you would change). As the motion designer, also fill in `swap` for each board's hook, month and ending: whether
the composition passes the swap test and why, in a sentence. Score honestly. The person's critic speaks in the first
person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`tally` writes `build/vote.md` and the panel's board to `build/winner.json`: the best scored board that passes the
swap test on all three compositions. A composition that fails names its cause: a line that misses its photograph's
edge (fix it in `build/picks.json`), a moment that could be anyone's (fix it in `taste.json` `moments`; a new `photo`
runs `picks.py` and the photograph read before the draft), or a word that would caption anyone's year (fix it in
`taste.json` `words`); then draft, check, sheets and the ballot again.

## The person picks

Where you can ask (`taste.json` `ask` is true), show the person `out/boards.png` and ask which look to make, in one
plain sentence ("Which of these three looks should I make: 1, 2 or 3?"). Where no one can answer (`ask` is false),
pick the look that fits `taste.md` best, or the panel's board when nothing in `taste.md` decides it. Then:

```
python3 S/scripts/vote.py pick <1|2|3> --why "<one line: their words, or why it fits them>"
```

`pick` takes the number in `out/boards.png`'s order or the style's id, writes that board to `build/winner.json` with
the reason, and clears every cut, music, preview, read and score made from another look. The same command, later,
is how the person's "make the second one" on the review page is run (see `SKILL.md`, "Which look").

Every `storyboard.py draft` starts a new vote: it removes `winner.json` and `vote/scores.json`, because the panel
judged the sheets it was shown. `snap` cuts only a board with a winner, so a fix at any later step runs the ballot,
the tally and the pick again before the film.
