# 3. Vote: the panel scores the three boards, then the person picks a look

Goal: the run's `vote.md` and `winner.json`, the look the person picked (or, where nobody can answer, the one you
picked by their taste).

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the seven rules, R1 to R7). Then, as each critic in turn, open every
board's `reel-sheet.png`, `sheet.png` and `storyboard.md` and fill in `vote/scores.json`: for each board, a whole number
1 to 5 for each rule, or `"not read"` when nobody in this session can read it from a board, and one paragraph (at least
25 words: what works, what fails, what you would change). The person's critic speaks in the first person from
`taste.md`.

```
python3 S/scripts/vote.py tally
```

A board stands only when its checks (with the swap test) and its sheets are green; `tally` writes the scores and the
paragraphs to `vote.md`, ranks the boards by their mean, and makes the first the winner until the person picks.

## The person picks the look

Show them `out/boards.png` (the three looks, numbered 1 to 3, each with its name and one plain sentence) and ask
which one they want. When they answer, make it the winner:

```
python3 S/scripts/vote.py pick 2
```

(the number in `out/boards.png`, or the look's id). Where nobody can answer you (a run with no conversation), pick
the look that fits their taste yourself and say why in one line from `taste.md`:

```
python3 S/scripts/vote.py pick 3 --reason "their captions are short, plain and lowercase, and the grid says the month as plainly as they do"
```

A pick of another look than the winner removes everything made for the old one (the music, the preview, the timed
read, the cut rounds), so movement 4 runs again from `music.py make` in the same run folder.

When they have the finished film and say "make the second one" (or the first, or the third, or name a look), run
`vote.py pick` with that number, then movement 4 from `music.py make` and movement 5, in the same run folder; nothing
of the first look's music or cut is reused.

Every `storyboard.py draft` starts a new vote: before it writes the new boards it removes `winner.json`,
`vote/scores.json`, `music.json`, `film.json` and the old boards' `check.json` and `sheets.json`, because the panel
judged the sheets it was shown and the music was made for the look that won. `music.py make` refuses a run with no
winner, so a fix that drafts again runs check, sheets, the ballot, the tally, the pick and `music.py make` again
before the film.
