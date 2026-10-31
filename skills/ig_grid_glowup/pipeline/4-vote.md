# 4. Vote and pick: the panel scores the three boards, then one look is picked

Goal: `vote.md`, then `winner.json` naming the board the film is made from.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the rules). Then, as each critic in turn, open each board's
`storyboards/<L>/sheet.png` (and `out/boards.png` for the three side by side) with `grid-before.png` beside them (when
there is a feed) and fill in `vote/scores.json`: a whole number 1-5 for each rule a board shows and one paragraph per
board (at least 25 words: what works, what fails, what you would change). Judge against `audit.md` (when there is a
feed) and `taste.md`. The person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`vote.md` ranks the three boards by their mean, best first, and prints the pick command for the best.

## Pick the look

Where you may ask the person (`taste.json` `ask` is true, as in a conversation), show them `out/boards.png`, say in
one plain line what each look is, and ask which one. Then:

```
python3 S/scripts/storyboard.py pick B --by person --reason "they picked the second look"
```

Where you may not ask (`taste.json` `ask` is false), pick by their taste: the board `vote.md` ranks first unless
`taste.md` says otherwise, with a one-line reason in their terms:

```
python3 S/scripts/storyboard.py pick A --by taste --reason "quiet serif type, like the captions they write"
```

`pick` copies the board to `board.json` and writes `winner.json`. Picking again later (the person says "make the
second one") clears what the earlier pick made, and the steps after it run again on the new board in the same run
folder.
