# Complexity budget

Read this before you file a finding or write a line of code. It is the operating ruling for this
estate, not a style preference.

## The ruling

Simplicity that solves the issue is correct. Architecture for architecture's sake is bad. Most
problems in these repos came from overcomplicating things, so added complexity is itself a defect —
not a neutral cost.

Preference order for any change, strongest first:

1. Delete the mechanism that causes the problem.
2. Relax or merge an existing mechanism.
3. Use a built-in (DB constraint, partial index, materialized view, stdlib facility).
4. Add new code.

Reach 4 only after stating why 1-3 do not work.

## If you are REVIEWING

- Report the DEFECT separately from the FIX. The defect is frequently accepted and the fix rejected.
- A fix that ADDS anything — file, class, layer, interface, config flag, dependency, table, column,
  validation surface, defensive branch, reconcile/retry loop, guard — must name (a) the concrete
  reachable input that produces wrong behavior today, and (b) why no subtractive fix works. Without
  both, do not file it.
- Existing backstops DOWNGRADE severity. A gap already covered by server-side dedup, a natural key,
  a unique index or a permanent constraint is minor, never critical.
- Weight by realism. A scenario you cannot trigger is not a finding — put it in a separate
  "hypotheses" list, never in the defect inventory.
- Recommending consolidation or deletion is preferred to recommending addition.
- A ZERO-FINDING verdict is valid and valued. Padding an inventory is a review defect.

### Do not file these — rejected on sight

- Defensive guards against hypothetical callers.
- "For completeness" tests with no coverage gap.
- Stylistic restructures of working code.
- Back-compat shims. Also: "this refactor changes prior X" is not a defect unless it violates a
  frozen contract or breaks a post-refactor consumer.
- SHA / hash / cascade-bookkeeping drift.
- Extract-a-helper or premature decomposition where the code is within size limits and follows the
  repo's convention.
- DRY consolidation below ~10 duplicated sites. Copy-paste of trivial declarations is fine; helpers
  earn their keep at scale, or when the duplicated logic carries subtle correctness invariants.
- Uncited speculation. Every finding needs file:line and a concrete trigger.

## If you are BUILDING

- Write the smallest coherent change that satisfies the spec. Do not add scope the spec did not ask
  for, and do not build for requirements nobody stated.
- Do not produce: one-caller indirection, forwarding-only layers, abstractions with exactly one
  implementation, single-value flags or enums, defensive branches for states that cannot occur,
  hand-maintained parallel copies of derivable data, or two mechanisms doing one job.
- Delete the old path in the same pass. Never leave legacy-vs-new side by side.
- Targets: SOLID, DRY, SRP, SSOT, no god classes (a service past ~7 methods or ~200 lines needs
  splitting). These are reasons to CONSOLIDATE, never licence to add layers.
- Follow this repo's stated conventions (CLAUDE.md, rules/, architecture docs) over generic
  industry defaults.

## The counterweight — complexity that IS load-bearing

Do not "simplify" these:

- Anything whose job is to REFUSE something: auth/RBAC guards, shared-host boundaries, ACL/RLS
  policies, idempotency guards, returned-authority re-checks. Apparent redundancy there is defence
  in depth.
- Anything pinned by a contract test that asserts source text verbatim — grep for a test that reads
  the file before rewriting it.
- Documented intentional behavior and deliberate carve-outs. Check before assuming drift.
- Anything you have not proved dead. A green replay proves APPLY, not CONTROLS.
