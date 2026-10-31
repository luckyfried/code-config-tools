# 3. Vote: the panel scores the three looks, and a look is picked

Goal: `vote.md` and `winner.json` in the run's folder.

```
python3 S/scripts/vote.py ballot
```

Read `S/critic/critic.md` (the three critics and the seven criteria). Then, as each critic in turn, open each board's
`storyboards/N/sheet.png` and `storyboard.md` and fill in `vote/scores.json`: a whole number 1-5 for each criterion
and one paragraph per board (at least 25 words: what works, what fails, what you would change). Score honestly. The
person's critic speaks in the first person from `taste.md`.

```
python3 S/scripts/vote.py tally
```

`tally` writes `vote.md` (every board's scores against the bar and what each critic said) and `winner.json`, the best
board for now. The bar: a mean of 4.5 or more with no criterion under 4; means are cut down to two places, never
rounded up.

## Which look

Show the person `out/boards.png` and ask which look they want, in one plain sentence that names the three ("cinematic,
home movie or scrapbook?"). Then:

```
python3 S/scripts/vote.py pick --board N --why "in one line, what they said"
```

When `taste.json` carries `"ask": false` (the run goes on without the person), do not ask: pick the look their taste
points to (their words for a look, their palette, their pacing, the moods of their pillars) and say why in one line:

```
python3 S/scripts/vote.py pick --board N --taste --why "warm grainy palette and slow captions: the home movie"
```

`pick` makes `winner.json` name the board and removes everything made from the look picked before (the music, the
timed films, the clips, the render, the films and stills in `out/`, the critics' rounds, the checks and the frames), so
nothing of one look reaches the film of another; `out/boards.png` and a track the person placed stay.

Every `storyboard.py draft` starts a new vote: it removes `winner.json` and `vote/scores.json`, because the panel
judged the sheets it was shown. `snap` cuts only the board in `winner.json` and refuses without one, so a fix that
drafts again runs the ballot, the tally and the pick again before the film.

A person who later says "make the second one" (or the third, or names a look) gets that board picked with `vote.py pick
--board N`, then movement 4 again from `music.py find`.
