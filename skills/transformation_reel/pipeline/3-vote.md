# 3. Vote and the look: the panel scores the three boards, and the person picks one

Goal: `RUN/vote.md`, and `RUN/winner.json` naming the look to make.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics, the seven criteria and the swap test). Then, as each critic in turn,
open each board's styleframes full size and its `storyboard.md`, and fill in `RUN/vote/scores.json`: a whole
number 1-5 for each criterion, and one paragraph (at least 25 words: what works, what fails, what you would change).
Score honestly. The person's critic speaks in the first person from `taste.md`.

The motion designer also answers the swap test on each styleframe, in `swap`: `holds` when the design is built on
that photograph (its piece, their line for it, its date, the move that answers it), `swappable` when another of their photographs could
stand in it with nothing else changed.

```
python3 S/scripts/vote.py tally
```

Tally recommends the board with the highest total among those whose styleframes all hold. When every board has a
swappable frame, tally names them and nothing goes on: the fault is in the posts or the research the builder read, so
fix it there and run movement 2 again.

## The person picks the look

Show the person `RUN/out/boards.png` (the three looks, A, B and C, each its opening, its busiest moment and its
ending), say which one the vote recommends and why in a few words, and ask which look to make. Then:

```
python3 S/scripts/vote.py pick <style>
```

With `"ask": false` in `RUN/taste.json` there is nobody to ask: pick by their taste (`lean` in taste.json, else the
recommendation) and give the reason in one line, `vote.py pick <style> --why "..."`; `brief.md` carries it.

The same command takes a later "make the second one": `pick` with that look's style clears what was made for the
other look in this run (the cut, the music, the timed draft, the checks, the critics' rounds and what `out/` delivered,
all but `out/boards.png`), and movement 4 runs
again from `music.py find`, then movement 5.

Every `storyboard.py draft` starts a new vote: it removes `RUN/winner.json` and `RUN/vote/scores.json`, because the
panel judged the board it was shown, and a tally that reaches no winner leaves none. `snap` cuts only a board with a
winner, so a fix at any later step runs the ballot and the tally again before the film.
