# 3. The panel scores the three looks, and the look is picked

Goal: `R/vote.md` and `R/winner.json`.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the six scored rules, R1 to R6). Then, as each critic in turn, open
each look's three sheets and its `storyboard.md` and fill in `R/vote/scores.json`: for each look, a whole number 1-5
for each rule, and one paragraph (at least 25 words: what works, what fails, what you would change). Each rule is
scored from the part of the board that shows it: the sheets for R1 to R3, the beats and their moves for R4, the sound
cues for R5, the clips for R6. Score each look against its own card: a scrapbook is judged as a scrapbook. Score
honestly; a score below 4 names a change to make before the cut. The person's critic speaks in the first person
from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`tally` writes the scores into `R/vote.md` and the panel's order into `R/vote/order.json`. It picks nothing.

## The pick

Where you can talk with the person, show them `R/out/boards.png` and ask which look they want: "A, B or C?". Then:

```
python3 S/scripts/vote.py pick B
```

`pick` takes A, B or C, first, second or third, the look's name or its style id. Where you cannot ask (`taste.json`
`ask` is `false`), pick the look that fits their taste best, the panel's order in mind, and say why in one line:

```
python3 S/scripts/vote.py pick scrapbook --why "their year is pasted-in film prints and handwritten captions"
```

`pick` writes `R/winner.json`, which `snap` reads. A pick of another look later ("make the second one") is the same
command: it removes the music, the cut and its critic rounds made for the look before, and movements 4 and 5 run again
in the same run folder.

Every `storyboard.py draft` starts a new vote: it removes `R/winner.json` and `R/vote/scores.json`, because the
panel judged the sheets it was shown. `snap` cuts only a picked board.
