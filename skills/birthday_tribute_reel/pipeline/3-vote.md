# 3. The look: the panel scores the three boards, the person chooses one

Goal: `B/vote.md` and `B/winner.json`.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the seven criteria). Then, as each critic in turn, open each board's
three sheets and `storyboard.md` and fill in `B/vote/scores.json`, for each of the three boards: a whole number 1–5 for each criterion and one
paragraph (at least 25 words: what works, what fails, what you would change). Score honestly. The person's critic
speaks in the first person from `taste.md`, as the one sending the film to the named one. Each critic also applies
the swap test (critic.md) and lists, in each board's `"swap"`, the cards whose photograph could trade places with a
neighbor's without changing the design.

```
python3 S/scripts/vote.py tally
```

The tally writes `vote.md` and the panel's board to `B/winner.json`. The swap-test cards are listed in `vote.md`: redesign each around its own photograph in `storyboard.json` before
movement 4; `storyboard.py snap` refuses while any of them is unchanged.

Every `storyboard.py draft` starts a new vote: it removes `B/winner.json` and `B/vote/scores.json`, because the panel
judged the sheets it was shown, and each board's type read (`type.json`), so `ballot` refuses until
`storyboard.py sheets` has drawn the new draft. `snap` cuts only a board with a winner, so a board drafted again goes
through the sheets, the ballot and the tally again before the film.

## Ask which look

Show the person `out/boards.png` (the three looks side by side, each named) and ask one question: which look? Their
answer, or the panel's board when they say any, is the film:

```
python3 S/scripts/vote.py pick N --reason "in one line, why this look"
```

When `B/taste.json` has `"ask": false`, choose by taste instead, from `taste.md`: the look the named one would most
want to receive, `vote.py pick N --by taste --reason "..."`. Picking a look removes anything already cut from another
one, so "make the second one" after the film is delivered is `vote.py pick 2` and then movement 4 from `music.py make`.
