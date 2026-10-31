# 5. Critics: the timed cut is read before anything ships

Goal: a critic round on the current `film.json` that passes every read and ships (every score 4 or more, or the one
fix spent), with its type read on the full-size cut. `film.py render` refuses until it has one.

Every round before the last reads the half-size proof (`film.py cut --proof`). While `proof.silent.mp4` is the newest
cut, `vote.py cut` reads it and its first line says "reading the half-size proof".

```
python3 S/scripts/vote.py cut
```

It opens the next round, `critic/cut-N.json`, for the cut of the current `film.json`. Read `S/critic/critic.md`,
section "The cut", and do it in its order:

1. **The reads**, on `frames/film-strip.png`, the beat strips and `still_per_second` in `qa/cut.json`: fill in each of
   `reads` (`frame`, `carry`, `sound`, `swap`, `held`, `monotony`), each a `pass` true or false and a `why` of at least
   eight words naming the seconds.
2. **Then look**: every `frames/strip-<beat>.png` full size with the Read tool. Then, as the motion designer and as
   the person, a score 1–5 per criterion and a paragraph each.

```
python3 S/scripts/vote.py verdict
```

- `SHIP`: on the proof, go on to the full-size cut below; on the full-size cut, go on to movement 6.
- `FIX` or `FIX ONCE`: it names the worst thing (a failed read comes first). Fix that one thing in the storyboard, the cast or
  the music, run the vote again (`vote.py ballot`, `tally`: snap cuts the board as the vote stored it), then
  `storyboard.py snap`, `music.py master`, `film.py cut --proof`, then `vote.py cut` for round 2 (say in `fixed` what
  changed), read and score again. `vote.py cut` on the same cut reopens its round and never spends the fix. After round 2 the fix is spent: a round that passes every read ships, and
  brief.md names what is still below 4. A cut that fails a read never ships.

## The full-size cut and its type

Once the verdict on the proof is `SHIP` (or the fix is spent), cut the film at full size and score it once more:

```
python3 S/scripts/film.py cut
python3 S/scripts/vote.py cut
python3 S/scripts/vote.py verdict
```

`vote.py cut` moves the round to the full-size `film.silent.mp4` and empties each critic's `type` score; the reads and
the other scores stand. As each critic, open the new strips in `frames/` full size, read every line at the size a phone
shows it (`S/motion/system/standards.md`, R3), and score `type` again. A `type` score that takes the round under the
bar is a `FIX ONCE` like any other: fix it, cut the proof again, and score round 2.
