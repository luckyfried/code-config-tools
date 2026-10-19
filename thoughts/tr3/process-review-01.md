# tr3 process review 01: three blind runs, three by-eye layout defects the hand run let through

## Stages, cost, failures

| stage | cost | runs | outcome |
|---|---|---|---|
| check 1 compile, help, clean npm ci, sample render | 3.1 s + 34.3 s | 1 | green |
| check 2 fixture | 20.0 s (machine load 82 on 64 cores) | 1 | green |
| check 3 hand run, winner board 1 (route) only rendered as a film | 109 s script time | 1 | GATE GREEN; I saw a dim day kicker and a map label touching the line, called both minor |
| check 4 blind-with attempt 1 (kit bfa1120) | 320 s | 1 | GATE GREEN; cut critic gave type 3, FIX ONCE; the agent lifted the kicker color in the board (no kit edit) |
| check 4 blind-with attempt 2 (kit 713e12b, kicker fixed) | 321 s | 1 | GATE GREEN; the agent edited kit map.tsx: "positano"/"amalfi" labels printed across the route line |
| check 4 blind-with attempt 3 (kit 7ea6ce4, labels fixed) | 324 s | 1 | GATE GREEN; postcards won; the agent edited kit Postcard.tsx: "positano" wrapped inside its stamp |
| check 4 blind-without | 43 s | 1 | a text answer only, no files |

Every gate was green. Three of three blind-with attempts carried a layout defect that a critic or the agent saw by
eye and fixed at its own cost (one fix round, two kit edits).

## Where the waste enters

Stage 3, the hand run. Two of the three defects were on my own frames and I passed them as minor; the third sat in
a board (postcards) the hand run never rendered as a film, and in a beat (the positano postcard) the six-frame
style sheet does not show. The blind run is the expensive stage (5+ minutes) and is the one that found them.

1. Input: the hand run's look covered the winning board only, at contact-sheet size. A blind run can pick any of
   the three boards.
2. Cheap check before the expensive step: rendering every beat of all three boards as stills at full size costs
   seconds (sheets render 18 frames in about 9 s) and shows every text block the films can carry.
3. Feedback: a defect the eye sees on a frame is a defect, whatever its size; "minor" is the word that sent two of
   them on to the blind runs.
4. Needed at all: the blind run stays; it is the proof.

## Change

- Fix the stamp at its root (size the place name to the stamp width, one line), as the agent did.
- Before any further blind run: one still per beat for every board in both formats (reel and landscape) plus the
  five story cards, viewed at full size, every text block checked for wrap, overlap and contrast. No defect is
  passed as minor.
- Then the last blind-with attempt (the third fix round of three).

## Measurement

The next blind-with attempt ends GATE GREEN with no kit file changed (diff of the placed kit against the export is
empty apart from node_modules and the cache) and no FIX ONCE.

## Codex conference

Sent with the table above. Codex agreed with the cause, with one correction: the
decisive failure was accepting defects already seen ("minor"), more than the narrow coverage. It accepted all three
changes as subtractive or cheap, and warned that `nowrap` alone would let a long place name run out of the stamp
(handled: the name's size is computed from the stamp width and the name's length, so it fits on one line). It also
noted that stills do not prove motion, so the blind film review stays the proof.

## What the full-size review found and fixed (kit 358f118)

137 stills (every settled shot of the three boards in both formats plus each board's story cards, 68 s to render)
showed three more defects, all fixed at the root before the last blind run:
- the stamp's place name wrapped (sized to fit on one line);
- the route map drew labels for places the line had not reached yet, so ghost labels piled up (a label appears when
  the line reaches its place);
- the napoli postcard used the caption of the second visit (oct 8) while the postcards run in route order (a place
  visited twice takes its first visit's photo and caption).

## Measured result

blind-with attempt 4 on 358f118: 379 s, GATE GREEN 15 of 15, no kit file changed (diff against the export shows
only node_modules/.cache and __pycache__), no FIX ONCE (verdict SHIP round 1, every cut score 4 or 5), and the
14 frames of the film read clean at full size. One defect remains, in board 2 (a runner-up): its closer puts the
handle line right under the "capri" map label. It is written down in ready.txt rather than fixed, because the fix
loop's three rounds are spent and a kit change now would ship a tree no blind run has seen.
