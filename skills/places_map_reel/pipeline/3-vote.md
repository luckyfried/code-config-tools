# 3. Vote and pick: the panel reads the three looks, and the person chooses one

Goal: `vote.md` and `winner.json` in the run's folder, naming the look the film is made in.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the seven rules). Then, as each critic in turn, open each look's
`storyboards/<style>/sheet.png` and `storyboard.md` and fill in `vote/scores.json`: a whole number 1 to 5 for each rule
and each look, and one paragraph per critic per look (at least 25 words: what works, what fails, what you would
change). As the motion designer, apply the swap test to each look's three compositions (the hook, the stop and the
closer). The person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`tally` writes `vote.md` and `winner.json`: the look with the highest total among those whose compositions pass the
swap test. A look with a composition that fails the swap test cannot win: fix what makes it a template (the cast, the
places) and run movement 2 again.

## The pick

Show the person `out/boards.png` and ask, in one plain sentence, which look they want. Their answer is the pick:

```
python3 S/scripts/vote.py pick --board N --why "what they said"
```

N is 1, 2 or 3, as the picture orders them, or the look's id. When `taste.json` carries `"ask": false`, do not ask:
pick the look their taste points to (`research.json` `lean` names one and why, the tally another) and give the reason
in one line in `--why`. The pick stands over the tally.

A pick made after a film was cut in another look removes that cut (`film.json`, the timed read and the rounds), so
movement 4 runs again from the music in the same run folder; `pick` prints the steps.
