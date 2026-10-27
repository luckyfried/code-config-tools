---
name: fanout-codex
description: Fan out HARD parallel coding work to codex (a strong, free coding model) as backgrounded MCP tasks — no subagents, no wrapper. The main session writes task-spec md files ONCE, then fires one mcp__clink__clink(cli_name="codex", write=true) call per unit in a single message; the harness runs them concurrently and auto-backgrounds each, and codex edits the repo directly. Use for reasoning-heavy units - math, ML, data science, architecture, performance, idiomatic/best-practices setup. Usage - /fanout-codex [count]. Defaults to as many units as the work decomposes into.
---

# Fan-out codex

Delegate **complex** coding work to **codex** — a strong coding model (above Sonnet, below Opus, and
**free**) — running headless with web search. The expensive Anthropic model (you) only orchestrates; the
hard implementation runs on codex, in parallel across many units.

**No subagents, no wrapper.** Each unit is one `mcp__clink__clink` call with `cli_name: "codex"` and
`write: true`. The `clink` tool is annotated `readOnlyHint: true`, so every clink call you emit **in a
single message** runs concurrently, and any call still running past the auto-background threshold moves to a background task
that notifies you on completion. N parallel codex units, zero Anthropic agents, no intermediate script.

clink runs the `codex` CLI under a codex login from the csc account pool, in your project folder with
your session's own toolkit (the same MCP servers, skills, and keys). With `write: true` codex edits the
real repo and runs commands directly.

## fanout-codex vs fanout-zai — pick the right tier

| | **fanout-zai** (GLM-5.2) | **fanout-codex** (codex) |
|---|---|---|
| Model strength | weak, literal | strong (≈ above Sonnet, below Opus) |
| Best for | high-volume, mechanical, well-bounded edits | hard, reasoning-heavy units: math, ML, data science, architecture, perf, best-practices/idiomatic setup |
| Spec style | spoon-feed every line; zero ambiguity | state **goal + constraints + acceptance**; let codex choose the *how* |
| Extras | — | web search (current best practices), its own MCP servers |

If a unit is genuinely hard or open-ended, send it here. If it's a pile of repetitive, fully-specified
edits, use `/fanout-zai`.

## The core idea — write the spec ONCE, pass the path

You (main session) are the expensive model. Don't copy a unit's instructions into each clink call's
`prompt` — that multiplies the token cost of the spec in *your* context.

1. **You** write each unit's spec to a **task-spec `.md` file on disk** — once.
2. You fire one clink call per unit, passing the spec file's absolute path in `absolute_file_paths`
   and only a one-line directive in `prompt`.
3. clink hands the spec to codex; the spec text never re-enters your context. codex edits the repo
   directly and its final message returns as the clink result (inline, or via the background-task
   notification if it ran long).

```
main session ──writes spec once──> thoughts/shared/agent-comms/<slug>/task-NN.md
     │                                          │
     │ mcp__clink__clink(cli_name="codex",      │ absolute_file_paths=[task-NN.md]
     │   write=true,                            │
     │   prompt="execute the attached spec")    ▼
     ▼                                    codex (web search + MCP)
 clink ──────────────────────────────────> edits repo, runs commands ──> disk
     │                                                                    │
     └──> clink result / bg-task notification (codex's <SUMMARY>) ◄───────┘
```

## Hard rules — learned, not optional

**1. Disjoint files per parallel unit — the cardinal rule.** codex writes to the real repo. `clink` is
annotated read-only, so the harness will happily run concurrent codex calls that are actually editing —
it will NOT serialize them for you. Two units that touch the same file WILL clobber each other (no
merge, last writer wins). When you decompose, every unit MUST own a **disjoint set of files**. Shared
file → same unit, or sequence them — never two parallel units on one file. State the file partition
explicitly before launching.

**2. Bound the blast radius — the spec is the only guard.** With `write: true` codex can edit any file
and run any command. Every task-spec MUST list the exact files codex may
edit and an explicit "do NOT touch anything else, do not run destructive commands." For a read-only
analysis unit, leave `write` off: codex then runs in its read-only sandbox.

**3. Specify the goal, not every keystroke.** Unlike zai, codex is strong — over-dictating wastes its
capability. Give it the **objective, the hard constraints, the interfaces it must honor, and concrete
acceptance criteria**, then let it choose the implementation. Still be unambiguous about scope, file
ownership, and what "done" means. For research-flavored units (best practices, library choice), say so —
codex has web search.

**4. Launch, don't block.** Fire all the clink calls in ONE message. Each runs concurrently and
auto-backgrounds, so a unit can run for many minutes without stalling the session. Do NOT emit clink
calls one message at a time waiting for each — that serializes them. Never place a codex clink call
inside a `Workflow` stage (the stall supervisor kills long calls and retries them).

**5. Observe disk, never trust the summary.** codex writes a `<SUMMARY>`; that is a claim, not proof.
After fan-in you independently verify the actual repo state (build / typecheck / the unit's test) before
calling any unit done. Re-dispatch units whose verification fails.

## Arguments

`$ARGUMENTS` format: `[count]`

- **count** (optional): cap on parallel units. If omitted, use as many units as the work naturally
  decomposes into (keep it sane).

## Step 1: Understand the work

From the conversation context and the user's request, determine the full body of work to delegate. Make
the scope and the interfaces concrete before decomposing — a precise acceptance bar is what lets codex
run unattended.

## Step 2: Decompose into disjoint units

Break the work into independent units such that **no two units edit the same file** (Rule 1). For each
unit note: a short slug, the exact files it owns, and the objective. State the partition to the user. If
`count` is set and there are more units, batch related units (keeping file sets disjoint) to ≤ `count`
calls.

## Step 3: Write one task-spec file per unit

For each unit, write `${CLAUDE_PROJECT_DIR}/thoughts/shared/agent-comms/<run-slug>/task-NN.md` (create
the dir). Use absolute paths. The spec IS the prompt — codex reads it from `absolute_file_paths`, so
write it as a direct instruction, not as a description of one:

```markdown
# Unit NN: <one-line objective>

## Goal & context
<What outcome is wanted and why. Where the relevant code lives (exact files/symbols to read first).
The approach is codex's to choose — but state any non-negotiable design constraints or interfaces.>

## Files you MAY edit (and NO others)
- /abs/path/to/file_a.ext
- /abs/path/to/file_b.ext
Do NOT create/delete/rename/edit any file not listed. Do NOT run destructive commands.

## Constraints & interfaces to honor
- <public signatures, schemas, invariants, perf budgets, libraries allowed/forbidden, style rules>
- <if current best practices matter, say "research current best practice for X via web search">

## Acceptance criteria
- <Observable, checkable outcomes — what must be true when done.>

## Verification command (run it; it must pass)
```
<exact command, e.g. the test / typecheck / benchmark scoped to this unit>
```

## Output
End your reply with `<SUMMARY>` listing every file you changed, key decisions, and the verification result.
```

## Step 4: Launch the units — all clink calls in ONE message

Emit **one `mcp__clink__clink` call per unit, all in a single message**:

```
mcp__clink__clink(
  cli_name = "codex",
  write    = true,
  prompt   = "Execute the coding task described in the attached task-spec file. It states the goal,
              the constraints, the exact files you may edit, what you must NOT touch, and the
              acceptance criteria. Make the edits directly in the repository. Edit ONLY the files the
              spec authorizes. Use web search if current best practices matter. Run the verification
              command the spec lists and confirm it passes. End with <SUMMARY> recapping every file
              you changed, key decisions, and the verification result.",
  absolute_file_paths = ["${CLAUDE_PROJECT_DIR}/thoughts/shared/agent-comms/<slug>/task-01.md"]
)
```

Repeat with `task-02.md`, `task-03.md`, … in the same message.

- Keep `prompt` to the directive above — the detail lives in the spec file. Never inline the full spec
  text into `prompt`.
- Add a unit's key target source paths after the spec path in `absolute_file_paths` when you want them
  in front of codex immediately; codex has full repo access and can open anything the spec references.
- `role` defaults to `default` (coding). Use `role: "planner"` for a design-only unit.

## Step 5: Confirm launch

Tell the user:

```
Launched [N] codex coding units as parallel clink tasks (specs in thoughts/shared/agent-comms/<run-slug>/).
Each runs concurrently and backgrounds if it runs long; you'll be notified as they complete.
```

Then stop. Do not wait.

## Step 6: When units return — verify disk, triage, re-dispatch

Per Rule 5, do not trust the `<SUMMARY>`. For each unit:

1. **Observe the actual disk state** — run the unit's verification command yourself, and/or read the
   changed files. Outputs don't lie; codex's summary might.
2. **Pass** → the unit is done.
3. **Fail or incomplete** → fix it on codex, not on yourself. Append the failure output (and what's still
   wrong) to the unit's `task-NN.md`, then re-fire that unit's clink call, passing its `continuation_id`
   from the prior result to continue the same thread (or a fresh call for a clean slate).
4. After all units pass individually, run one **aggregate** check (full build / typecheck / test suite) —
   parallel edits to disjoint files can still interact. Fix any integration breakage via a follow-up unit.

Only when the aggregate check passes is the fan-out complete.
