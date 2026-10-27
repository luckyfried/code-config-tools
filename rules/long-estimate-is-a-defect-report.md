# A Long Estimate Is a Defect Report

Applies to every job I run or hand off: scripts, backfills, migrations, builds, test runs, crawls,
deploy lanes, agent fan-outs. Companion to `overlap-pipeline-stages.md`: that rule removes waiting
between steps; this one removes the waste inside a step.

## Pattern

Ed, 2026-09-20: "you told me that some task was going to take many many hours. and the correct move
is to examine why does it need to take that long, how is it inefficient, and how could we make it
faster, and to actually DO that, automatically, always."

The moment I am about to say (or think) that something will take more than a few minutes, the
estimate is not a status to report. It is a finding to explain. Before the sentence "this will take
N hours" reaches Ed, I have already asked why, measured where the time goes, and either fixed it or
shown that the time is irreducible.

1. **Trigger.** Any projected runtime over about 10 minutes, or any job whose measured rate puts
   the finish more than about 10 minutes out. Measure the rate in the first minute or two of a run;
   never wait for a job to be slow for an hour before looking.
2. **Do the arithmetic.** Units of work ÷ measured rate = projected time. Then ask what the
   hardware could do: a database writes thousands of rows per second, a disk reads hundreds of MB
   per second, a network call takes tens of milliseconds. A projection 10x or more off that is a
   design defect in the job, not a property of the work.
3. **Find where the time goes, by measurement.** Count round trips, processes spawned, connections
   opened, statements per row, pages per scan, retries, sleeps, serial awaits. The usual causes, in
   the order they usually pay:
   - one round trip, statement, process or connection per item instead of one per batch or set;
   - a paged or cursor loop where one ordered streaming query does;
   - work done in the client that the database (or the tool) does set-based;
   - serial work with no dependency between items;
   - recomputing every run what could be computed once or diffed;
   - a missing index, a full scan per lookup, a plan that misestimates;
   - a rate limit or budget I control being treated as a law of nature.
4. **Fix it, then run it.** Stop the slow run as soon as the fix is worth more than the progress it
   has made (check it is safe to stop, and that a rerun skips finished work). Make the change
   through the normal lane for the repo (a builder packet where code edits are delegated), prove
   the new rate with a measurement, relaunch. This needs no go-ahead: a faster way to do stated
   work is the stated work.
5. **Only then report**, and report the numbers: old rate, the cause, the change, new rate, new
   finish time. When the time really is irreducible (an external quota, a vendor build, a real
   compute floor), say which limit it is, with its number, so a design change can be decided.

## DO

- Treat my own estimate of "hours" as the start of an investigation, in the same turn.
- Measure the rate early and project the finish out loud, with the arithmetic.
- Prefer the fix that removes mechanism (one statement for the batch, one query for the scan) over
  one that adds it (worker pools, queues, caches).
- Make long jobs safe to stop and rerun, so abandoning a slow run costs nothing.
- Put a timeout on every network wait inside a long job; a hang is the slowest rate there is.

## DON'T

- Don't report a long runtime as a fact of life and go do something else while it grinds.
- Don't wait for Ed to ask "why is this slow?" or "why aren't we batching?". If he asked, I missed
  the trigger.
- Don't optimise by guessing. The cause is whatever the measurement says it is.
- Don't design around a limit I control (pool size, batch size, budget, concurrency); raise it.

## Example (the case that produced the rule)

Full-corpus registry tag pass, 2026-09-20, about 2.2 million tag rows. First run: a paged keyset
read (about 33 minutes) and one writer-function call per row, which landed 52,800 rows in about 24
minutes of writing: roughly 37 rows a second, a finish about 17 hours away. I reported that as the
cost of the job. Ed asked "why arent we batching? also -- seems like these queries could be
significantly improved right". The fix was small: one ordered streaming query for the read, one
statement per 2,000-row batch for the write (`values` list cross-joined to the writer function).
Second run: read 5 min 38 s, writes at 2,700 to 3,200 rows a second, the whole write in about 12
minutes. About 80x, from two changes that were visible in the first minute of the first run.

## Source Sessions

- 2026-09-20 configurator (a17b5bc1): tag first pass, PR #1697 (set-based read and write).
