---
name: codex-review
description: Send current work for EXTERNAL code review by codex (NOT a self-review). Each review is one mcp__clink__clink(cli_name="codex") call fired from the main session — no subagents, no wrapper. Usage - /codex-review [count] (e.g., /codex-review for 1, /codex-review 5 for 5 parallel reviews). Defaults to 1.
---

# Codex Review

Send current work to an EXTERNAL codex model for code review. Each review is one `mcp__clink__clink`
call; the harness runs them concurrently and backgrounds each, so you keep working while they run.

## CRITICAL: This is an EXTERNAL review

**The entire point of this skill is to get a review from a DIFFERENT model (codex), NOT from yourself.**

- The review MUST come from a clink call. That is non-negotiable.
- You must NOT read the files and write your own review. That defeats the purpose.
- If the clink call fails, report the failure — do NOT fall back to a self-review. A failed call is a
  result you report, not a gap you fill in yourself.
- Nothing in the vehicle can stop you from writing the review yourself, so this rule is yours to keep.
  The proof that it held is codex's own output — cite the clink result when you report findings.

## Vehicle: one clink call per review

`mcp__clink__clink(cli_name: "codex", role: "codereviewer", absolute_file_paths: [...])`. clink runs
the `codex` CLI under a codex login from the csc account pool, in your project folder with your
session's own toolkit, so codex reaches the same MCP servers you do.

The `clink` tool is annotated `readOnlyHint: true`, so every clink call you emit **in a single message**
runs concurrently, and any call still running past the auto-background threshold moves to a background task
that notifies you on completion. N parallel reviews, zero Anthropic agents, no intermediate script.

The review runs with `write` left off, so the reviewer's own file and shell tools run in the read-only sandbox.

## The core idea — write the prompt ONCE, pass the path

1. **You** write each review's full prompt to a `review-NN.md` file on disk — once.
2. You fire one clink call per review, passing the file's absolute path in `absolute_file_paths` and
   only a one-line directive in `prompt`.
3. codex reads the prompt file and the files it names; the prompt text never re-enters your context.
   codex's review returns as the clink result (inline, or via the background-task notification).

```
main session ──writes prompt once──> agent-work/<slug>/review-NN.md
     │                                          │
     │ mcp__clink__clink(cli_name="codex",      │ absolute_file_paths=[review-NN.md]
     │   role="codereviewer")                   ▼
     ▼                                    codex (web search + MCP)
 clink ──────────────────────────────────> reads the named files ──> review
     │                                                                 │
     └──> clink result / bg-task notification (codex's review) ◄───────┘
```

## Review Protocol — applies to every review

These are not optional.

**1. Fire all calls in one message; NEVER inside a Workflow stage.** A review of a large diff runs
many minutes. Emitting every clink call in a single message runs them concurrently and backgrounds
each, so nothing stalls and each review lands independently. Do NOT emit them one message at a time
waiting for each — that serializes them.

**The Workflow stall wall is a fixed 180s of model silence.** Neither
`CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` nor the per-call `stallMs` option moves it. A clink review
inside a `Workflow agent()` stage therefore sits silent for minutes, gets killed, and is **retried
6× with identical inputs**, re-running real-repo edits. Fire reviews between stages, never inside
one; for fanout→fanin→review, end the workflow and fire the review after.

If a workflow arm dies "stalled on all 6 attempts" at a review tail, CHECK THE DISK FIRST: the
implementation usually already landed; only the review needs re-running.

**2. No back-compat reviewer framing.** Never label a reviewer "back-compat"/"backward compatibility" —
the label leaks the wrong incentive and produces false positives. Frame that slot as "integration /
contract conformance" and include: "Findings of the form 'this refactor changes prior X' are NOT defects
unless they violate a frozen contract or break a post-refactor consumer."

**3. First-pass reviewer in tiered composition.** Wherever a Sonnet agent builds against a
Fable-authored spec, codex takes the FIRST-PASS review seat: Fable spec (persisted to a file) → Sonnet
build → `/codex-review 1` instructing codex to review the built work AGAINST THE SPEC (pass the spec
file path + the complete build/test/compile-check output, never a summary) → a Sonnet agent addresses
the gaps → Opus runs the single FINAL review. Opus never takes the first-pass seat — that is the token
saving. Prefer delegating any review to codex whenever a clear Fable spec artifact exists; if none
exists, author one first. Rule 1 still binds: launch the review between workflow stages, never inside
one.

**4. Concise & complete & thorough, under a HARD ROUND CAP: at most TWO codex review rounds per unit
of work, and ONE is the default.** codex is overly picky, so fewer is always allowed — when in doubt,
skip a round rather than add one. After the final round the orchestrator dispositions any remaining
findings itself — fix crit/majors in one consolidated revision, reject the rest with
rationale — and CLOSES the thread regardless of codex's GO/NO-GO verdict. Never loop toward a GO past
the cap; a NO-GO whose crit/majors are fixed does not block the build. Economy
inside the cap comes from maximizing NEW information per pass and verified findings closed per
revision. The three properties are co-requirements, each with its own machinery:

- **Thorough — per pass; depth is a property of the QUESTION.** Broad "find issues + verdict"
  prompts satisfice at the salient top-~10, and parallel broad reviewers overlap on the same top-3.
  The deepest findings are lens-local — they surface only when a pass is pointed at a named
  grounding surface. So give each reviewer ONE narrow lens with a NAMED grounding surface, plus the
  standing clauses (Step 3). Lens menu: internal
  consistency; library grounding vs the INSTALLED package source (name the path); infra/durability
  grounding vs the DEPLOYED estate (name the .nomad.hcl / config files); crash-and-race
  interleavings at every process boundary; migration/rollback operability; state-machine
  completeness (every state × event has exactly one owner).
- **Complete — per campaign; completeness is MEASURED, not felt.** The union of the reviewers'
  coverage matrices must cover every section / mechanism / ledger row with no unowned NOT-CHECKED.
  Verify every finding at source (zero-trust), then dry-loop the SAME unrevised artifact — known
  findings listed as "already found — find what these missed" — until a pass adds nothing new; that
  zero is the completeness evidence. Sweep every found defect CLASS across the whole surface; never
  fix only the found instance.
- **Concise — per cycle; spend review capacity only on what reviewers are FOR.** Phase-0 self-audit
  before any codex spend: grep-audit the artifact yourself (every term defined once, cross-refs
  resolve, no state with two meanings, no stale revision markers) and build an **assumption ledger**
  INTO it — one row per external-behavior claim (library, broker API, infra, code) with file:symbol
  evidence or explicit UNVERIFIED; reviewers must never burn capacity on grep-findable defects. Keep
  parallel lenses disjoint so passes add instead of overlap. Batch ALL verified findings into ONE
  consolidated revision per cycle — a revision resets review coverage, so revisions, not reviews,
  are the expensive unit. Fix at CLASS level, and prefer consolidating mechanisms over adding new
  ones — every new mechanism is new defect surface.

The cycle: Phase 0 (self-audit + assumption ledger) → Phase 1 (narrow-lens sweep) →
Phase 2 (one consolidated revision) → Phase 3 (optional: certify the revision). The whole
cycle IS the 2-round cap (sweep = round 1, certify = round 2, no spare); Phase 3 is skipped
by default and spent only when the round-1 fix touched something a second pair of eyes
should see. When the cap is reached, disposition and close — never repeat the cycle chasing
a GO.

## Arguments

`$ARGUMENTS` format: `[count]`

- **count** (optional): Number of parallel reviews to launch. Defaults to `1`.

Examples:
- `/codex-review` — 1 review
- `/codex-review 3` — 3 parallel reviews
- `/codex-review 5` — 5 parallel reviews

## Step 1: Parse Arguments

Parse `$ARGUMENTS`: if numeric, use as count; if empty or non-numeric, default to `1`.

## Step 2: Gather Context

You already know what was worked on — it's in your conversation context. Assemble:

1. **What was created/changed** — the files you created or edited, with absolute paths
2. **What the changes do** — purpose and design decisions

Do NOT inline file contents. codex reads the files itself from the paths you name.

## Step 3: Write one review-prompt file per review

Write `agent-work/<run-slug>/review-NN.md` at the project root (create the dir, and add `agent-work/` to
the project's `.gitignore` if it is not there).
The file IS the prompt — codex reads it from `absolute_file_paths`. Give each parallel review a
distinct lens (e.g. correctness, spec conformance, integration/contract conformance, tests) rather
than N identical passes:

```markdown
TWO HARD CONSTRAINTS, BOTH BINDING FROM THIS LINE: (1) SIMPLIFICATION IS THE GOAL OF THIS REVIEW. We
are making this code simpler, not more defended; excess complexity is itself a defect you are hunting,
and a fix that removes a mechanism beats one that adds it. The attached `complexity-budget.md` governs
every finding you file — read it first. (2) Do NOT edit any file, and do NOT run any git command
(`git diff`, `git status`, `git show`, `git log`, …) — git is banned absolutely in this repository, for
reviewers too. There is no diff to review: read the files on disk as they are, from the paths below,
with `sed -n` / `grep`.
(3) Do NOT connect to any database or live service, production included: a reviewer reads files on
disk; the lead measures.

You are performing an external code review, for correctness AND for excess complexity. Be specific —
reference file names and line numbers.

## Review lens for this pass
<For substantial artifacts pick from the Rule-4 narrow-lens menu and NAME the grounding surface
(installed package path, deployed .nomad.hcl estate, schema files). Otherwise e.g. correctness &
edge cases | spec conformance | integration & contract conformance | test coverage.>
<If this is the integration slot, include: findings of the form "this refactor changes prior X" are NOT
defects unless they violate a frozen contract or break a post-refactor consumer.>

## Standing clauses (MANDATORY in every review prompt)
1. Your deliverable is the COMPLETE defect inventory for your lens — do NOT stop once you have
   enough for a verdict. The verdict is a one-line afterthought after the inventory is exhausted.
   Completeness applies to REAL defects in your lens; it is not a quota — never reach the end of a
   clean section and manufacture something to fill it.
2. Output a coverage matrix: one row per section / mechanism / assumption-ledger row, each marked
   SOUND, DEFECT, or NOT-CHECKED. NOT-CHECKED rows count against the review; SOUND is a valued
   verdict, not a wasted row.
3. Defect-class history: <classes found in prior rounds, if any>. Sweep for every remaining
   instance of each class.
4. The COMPLEXITY BUDGET in the attached `complexity-budget.md` binds every finding: report the
   defect separately from the fix, justify any additive fix against the smallest-coherent-change
   rule, let existing backstops downgrade severity, and treat a zero-finding verdict as valid.
   Its "do not file" list is authoritative — read the file before filing anything.

## Files to review (absolute paths — read them yourself)
<Stamp every path with the size and mtime you measured at prompt-writing time — see "Stamp the
tree state" below. Format: `- /abs/path — 12345 bytes, mtime 2026-08-02T14:03:11`.>
- /abs/path/to/file_a.ext — <bytes>, mtime <iso8601>
- /abs/path/to/file_b.ext — <bytes>, mtime <iso8601>

## House conventions — read before filing any "best practice" finding
<Paths to this repo's CLAUDE.md, rules/*.md, architecture docs.>
"Best practice" means THIS repo's stated conventions, not generic industry defaults. Behavior
documented as intentional is not a defect. If you think an intentional decision is wrong, file it as
ONE labeled design question at the end — not as N findings through the inventory.

## Summary of work
<What was done, why, design decisions.>

## Output
Two inventories, then a one-line verdict.

**A. DEFECTS** — severity (critical = data loss / corruption / security / outage on a reachable path;
major = wrong output or crash on a realistic reachable input; minor = everything else), file:line,
what is wrong, and the SMALLEST fix that removes it.

**B. SIMPLIFICATIONS** — code that should be DELETED, merged or inlined. Hunt the inflation patterns
and respect the counterweight, both listed in `complexity-budget.md`. B is as valuable as A — an empty
B on a large surface means you did not look.
```

### Stamp the tree state — a finding is a claim about a SNAPSHOT

Reviews and remediation lanes run concurrently *by design* — that is the point of backgrounding a
review and continuing. The concurrency is correct. The bug is consuming a finding about the snapshot
as a finding about the present. A review whose files moved under it yields findings that are already
fixed and line citations that land on unrelated code — and if the artifact does not record which tree
it reviewed, a stale finding is indistinguishable from a live one.

So before writing the prompt, capture size + mtime for every file you are about to name, and put
them in the prompt. Git is forbidden to agents in this repo, so mtime+size is the honest substitute —
it is enough to detect "this file moved under the review".

```bash
for f in /abs/path/a.py /abs/path/b.py; do
  printf '%s — %s bytes, mtime %s\n' "$f" "$(stat -c%s "$f")" "$(date -Iseconds -r "$f")"
done
```

## Step 4: Launch the reviews — all clink calls in ONE message

Emit **one `mcp__clink__clink` call per review, all in a single message**. `CLAUDE_CONFIG_DIR` is this
session's own folder, where Code Config places this skill. The tool takes absolute paths, so resolve
the budget's path to its absolute form first
(`echo "$CLAUDE_CONFIG_DIR/skills/codex-review/references/complexity-budget.md"`) and pass that:

```
mcp__clink__clink(
  cli_name = "codex",
  role     = "codereviewer",
  prompt   = "Read the attached complexity-budget.md FIRST — simplification is the goal of this
              review and that file governs every finding you file. Then perform the external code
              review described in the review-prompt file: it states your review lens, the standing
              clauses, the files to review, and the required output
              shape. Read the files yourself. Do NOT edit any files, and do NOT run any git
              command — git is banned in this repository.",
  absolute_file_paths = [
    "$CLAUDE_CONFIG_DIR/skills/codex-review/references/complexity-budget.md",
    "/abs/path/to/project/agent-work/<slug>/review-01.md",
  ]
)
```

Repeat with `review-02.md`, `review-03.md`, … in the same message.

- Keep `prompt` to the directive above — the detail lives in the prompt file. Never inline the review
  prompt text into `prompt`.
- For a review whose files are worth attaching directly (small, fixed set), add their absolute paths
  after the prompt file in `absolute_file_paths`.
- `role: "codereviewer"` selects clink's review system prompt. Use `role: "default"` for a review that
  is really an investigation.

## Step 5: Confirm Launch

After launching, tell the user:

```
Launched [count] codex review(s) as parallel clink tasks (prompts in agent-work/<slug>/).
Each runs concurrently and backgrounds if it runs long; findings are delivered to me on completion.
```

Then stop. Do not wait for results — keep working; each review arrives as its clink result or a
background-task completion notification.

## Step 6: When Reviews Return — Finding Disposition

Each review reaches you as its clink result (inline, or as a background-task notification carrying
codex's output). Codex review is REQUIRED on implementation units, but findings get **per-finding
triage** — never blanket-accept, never loop endlessly toward APPROVED.

**Default polarity: default-REJECT additive findings, default-ACCEPT subtractive / consistency /
real-defect ones.** Split every finding in two — codex's CONCERN is often real while its FIX is
over-engineered. Accept the concern, reject the fix, substitute the simpler root.

- **Accept + fix:** real bugs, spec-contract violations, missing promised instrumentation,
  misleading test names/docstrings.
- **Reject with a one-line rationale:** every class in `complexity-budget.md`'s "do not file" list —
  codex was given that list and should not have filed them. Before accepting any "missing validation"
  fix, check whether the behavior is documented as intentional (CLAUDE.md, `rules/`); if it is, reject
  and add a docstring note + pin-down test instead.
- **Marginal:** cheap → fix now; expensive → skip with brief rationale.

**Accepted findings must terminate somewhere real**: fix immediately. Never summarize findings and move
on.

**Write the RESULT to disk the moment it returns**, next to its prompt as
`agent-work/<slug>/review-NN-result.md`, and re-stamp the reviewed files (same
size+mtime command as Step 3) at the top of it. Until you do, the findings exist only in a
conversation that will be compacted, and nobody — including you, later — can re-check a finding
against the tree it was made about. A prompt on disk with no result on disk is half an artifact.

**APPROVED is not proof.** Codex hallucinates command output and stamps APPROVED on work that is not
on disk. After every verdict, independently verify disk state (grep / build / test) before marking the
unit done.

**REQUEST-CHANGES is not proof either.** A negative verdict earns exactly the same source
verification as a positive one, for the same reason: it is a claim about a snapshot. Before
dispatching *any* remediation from a review, diff the result's stamp against the files' current
size+mtime, and spot-check 2–3 citations by reading the cited lines and confirming they say what the
finding says. It costs under a minute and saves a wasted agent run. If the stamps moved, re-derive
every finding at source before acting — do not dispatch, and do not assume the drift is cosmetic.

**For large units, follow Rule 4 — consolidated batches inside the 2-round cap:** verify the union at
source, close the full inventory in one consolidated revision, then at most one optional
certification round — then disposition and CLOSE regardless of verdict. The banned failure modes are
shallow prompts, overlapping broad passes, per-finding patch churn, and looping past the cap toward a
GO. To continue a review thread instead of starting cold, pass that review's `continuation_id` from
its prior clink result.
