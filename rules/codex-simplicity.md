# Codex Overengineers — Budget the Complexity

Canonical ruling: `skills/codex-review/references/complexity-budget.md`. That file is written for the
external model and attached to its calls; this rule is the orchestrator's half. Applies to
`/codex-review`, `/fanout-codex`, and any `clink` consult.

## Pattern

codex produces working-but-inflated code and picky, additive review findings — one-caller
indirection, single-implementation abstractions, defensive branches for impossible states, extra
tables and config axes, "you should also handle X". Every added mechanism is new defect surface.
Architecture for architecture's sake is bad; simplicity that solves the issue is typically correct.

## DO

- Attach `complexity-budget.md` to every external-model clink call, and carry the ruling in the
  prompt's first line. A prohibition buried in prose does not bind codex — it has to lead.
- Accept the DEFECT, reject the FIX. codex's concern is often real while its fix is over-engineered;
  substitute the simpler root.
- Default-REJECT additive findings; default-ACCEPT subtractive, consistency and real-defect ones.
- Never pass findings to a fix agent unfiltered — blind pass-through adds indirection without solving
  a real problem, and makes the product worse.
