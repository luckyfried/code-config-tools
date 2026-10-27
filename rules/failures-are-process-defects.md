# Many Failures Means the Process Is Wrong: Step Back, Confer with Codex, Fix the Process

When you see lots of failures, take a step back and figure out how to make the PROCESS better.
Confer with codex on issues like that, every time. Improvement of every step is critical.

## Pattern

A batch of failures is never a list of tickets to patch one by one. It is evidence that a step of the process is
wrong: the wrong input to a step, the expensive step before the cheap one, a failure whose cause never reaches the
thing that could fix it. The case that produced the rule: 24 of 69 model drafts died before a vote, one app got zero
edits from twelve drafts, and the first response was five patches to the loop. The right response was to draw the
pipeline, put the numbers on each stage, find the stage where the waste enters (a planner that never saw the files,
drafts that never learn why they were reverted), and change the process there.

## DO

- Trigger: any batch where more than about a fifth of attempts fail, or any single unit that fails outright, or the
  same reason appearing three times. Stop adding rows; do the review before the next batch.
- Draw the process as stages with their measured cost and their failure count per stage (a table). Waste enters at
  one or two stages; name them.
- For each failing stage ask, in this order: is the step given the right input; is a cheap check possible before the
  expensive step; does the failure's cause reach the step that could act on it; is the step needed at all.
- Confer with codex through `/codex-review` (or `mcp__pal__clink` with `complexity-budget.md` attached and the
  simplicity ruling on the first line) every time, with the table and the numbers, before choosing the fix. Accept the
  defect, judge the fix; subtractive changes default-accept, additive default-reject.
- Write the review down (a `process-review-NN.md` beside the program's notes): stages, numbers, cause, the change,
  the measurement that proves it. Then change the process and measure again on the same inputs.
- Apply this to every step of a program, not only the model: harnesses, checks, lanes, builds, handoffs.

## DON'T

- Don't report a failure table as a status and queue the patches. The table is the start of the review.
- Don't fix the symptom at the stage where it is observed when the cause is upstream.
- Don't run the next batch on a process that just failed a fifth of its attempts.
- Don't skip the codex conference because the fix looks obvious; the conference is the rule.
