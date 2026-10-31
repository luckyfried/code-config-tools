# 3. Vote and pick: the person chooses the look

Goal: `vote.md` and `winner.json` in the run folder.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the criteria). Then, as each critic in turn, open `out/boards.png`,
each look's `sheet.png` and its `storyboard.md`, and fill in `vote/scores.json`: for every look, a whole number 1–5 on
each board criterion (`idea`, `picture`, `type`, `motion`, `own`) and one paragraph (at least 25 words: what works,
what fails, what you would change). Score honestly. The person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`tally` writes `vote.md`, the three looks' scores side by side, and says which look the critics lean to. It never
picks: the scores are there for when the person asks what the critics think.

## Ask which look

Show the person `out/boards.png` and ask one question: which look? Name each by its letter and its plain name ("A,
kinetic type; B, editorial quiet; C, swiss grid"). Then:

```
python3 S/scripts/vote.py pick <a|b|c>
```

When `taste.json` `ask` is false, do not ask: pick the look their taste points to and say why in one line, from
`taste.md`:

```
python3 S/scripts/vote.py pick <a|b|c> --why "<the one line, from their taste>"
```

`pick` refuses a look that was not drafted, and with `ask` false refuses without `--why`. Picking another look later
clears the old look's music (when it was made here), its cut and its rounds, so the film is made again in the new one.

Every `storyboard.py draft` starts a new pick: it removes `winner.json` and `vote/scores.json`, because the person
picked from the boards they were shown. `snap` cuts only a picked look.
