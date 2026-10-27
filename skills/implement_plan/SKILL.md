---
name: implement_plan
description: Implement technical plans end-to-end from agent-work/ with codex verification after each step, inline doc updates, and no stopping until complete. Usage - /implement_plan [path-to-plan]
---

# Implement Plan

You are tasked with implementing an approved technical plan from `agent-work/`. Execute the entire plan from start to finish. Every step is verified by codex before being marked complete. The plan document is updated inline as work progresses.

## Core Execution Rules

These are non-negotiable. Follow them exactly.

### Rule 1: Do Not Stop

Execute the ENTIRE plan. Do not stop for summaries, questions, or confirmation. If something is ambiguous, make the best engineering decision and document it in the plan. Only stop if a step is truly impossible (e.g., missing credentials, external service down).

### Rule 2: Inline Documentation

Update the plan document **immediately after completing each step** — not at the end, not in batches. For each completed step, add directly below it in the plan:

```markdown
- [x] Step description
  > **Completed**: [timestamp]
  > **Implementation**: [what was done, specific files changed, approach taken]
  > **Verified by**: codex review
```

This ensures the plan document is always a live record of progress.

### Rule 3: Verify Every Step with Codex

After implementing each step, call `mcp__clink__clink` to verify before marking it complete:

```
mcp__clink__clink(
  cli_name: "codex",
  role: "codereviewer",
  prompt: "Verify this implementation step is correct, complete, and achieves its objective.

## What was implemented
[Description of what you just did]

## Plan reference
The full plan is at: [absolute path to plan doc]. Read it for the spec and requirements.

## Files changed
[List of files modified/created with absolute paths]

## Verify against
- Does this match the spec in the plan document?
- SOLID principles
- DRY (Don't Repeat Yourself)
- SRP (Single Responsibility Principle)
- SSOT (Single Source of Truth)
- All other engineering best practices
- Are there any gaps, bugs, or issues?

Be thorough and specific. Reference exact lines and files.",
  absolute_file_paths: [list of changed files AND the plan document]
)
```

Preserve `continuation_id` across ALL clink calls for the entire execution — codex builds up context about the full implementation as it progresses.

### Rule 4: Triage All Codex Feedback

Every finding gets an explicit disposition before the next step — disposition means triage, not blanket acceptance:

- **Accept + fix now:** real bugs, plan/ticket-contract violations, missing promised behavior, misleading test names/docstrings.
- **Reject with a one-line rationale recorded inline in the plan doc:** defensive guards against hypothetical callers, "for completeness" test asks with no coverage gap, stylistic restructures, SHA/bookkeeping drift. Before accepting a "missing validation" fix, check whether the current behavior is documented as intentional — if so, reject and pin it down with a docstring note + test instead.
- **Marginal:** cheap → fix; expensive → skip with rationale.

Do not loop endlessly toward APPROVED. A step is complete once (a) your own disk verification is green AND (b) every finding is fixed or rejected-with-rationale. **Codex APPROVED alone is never sufficient** — codex has hallucinated command output before; always cross-check disk state yourself with grep / build / test after every verdict.

### Rule 5: Survive Compaction

If context compaction occurs, immediately re-read the plan document to restore state. The inline updates you wrote are your recovery mechanism — find the last `[x]` checkbox to determine where you left off.

### Rule 6: Quality Over Speed

Take as many tokens as needed. Thoroughness and correctness matter more than speed. Read full files, trace full call chains, write complete implementations. No TODOs, no placeholders, no "we'll add this later."

## Execution Modes

### Mode 1: Direct Implementation (Default)
For small plans (3 or fewer tasks) or when user requests direct implementation.
- You implement each phase yourself
- Context accumulates in main conversation
- Use this for quick, focused implementations

### Mode 2: Agent Orchestration (Recommended for larger plans)
For plans with 4+ tasks or when context preservation is critical.
- You act as a thin orchestrator
- Agents execute each task and create handoffs
- Compaction-resistant: handoffs persist even if context compacts
- Use this for multi-phase implementations

**To use agent orchestration mode**, say: "I'll use agent orchestration for this plan" and follow the Agent Orchestration section below.

---

## Getting Started

When given a plan path:
- Read the plan completely and check for any existing checkmarks (- [x])
- Read the original ticket and all files mentioned in the plan
- **Read files fully** - never use limit/offset parameters, you need complete context
- Think deeply about how the pieces fit together
- Create a todo list to track your progress. For each plan step, create TWO tasks:
  - The implementation task itself
  - A codex verification task immediately after it
- Start implementing — do not ask for confirmation

If no plan path provided, look for the most recent plan under `agent-work/`.

## Implementation Philosophy

Plans are carefully designed, but reality can be messy. Your job is to:
- Follow the plan's intent while adapting to what you find
- Implement each phase fully before moving to the next
- Verify your work with codex AND against automated checks
- Update the plan document inline as you complete sections

When things don't match the plan exactly, make the best engineering decision and document why you deviated. The plan is your guide, but your judgment matters too.

If you encounter a serious mismatch that could affect the overall design:
- Document the issue inline in the plan
- Make the best decision you can
- Flag it clearly so it's visible on review:
  ```markdown
  > **DEVIATION**: [what changed and why]
  ```

## Verification Approach

After implementing each step:

1. **Run automated checks** — success criteria, tests, build commands
2. **See the product the way its user will.** When a step produces a page, a screen, or a command, open it for real: a page in the browser this machine has (Playwright's Chromium when `CHROME_PATH` is set or `npx playwright` answers, otherwise the system browser), at the widths and color schemes the plan names, reading the console; a command by running it. A fake DOM in Node is not this check, and "no browser is installed" is a claim to prove by looking before it is written down.
3. **Fix any failures** before proceeding
4. **Run codex review** via clink (see Rule 3 above)
5. **Address all codex feedback** (see Rule 4 above)
6. **Update the plan document inline** with completion details
7. **Mark both tasks** (implementation + verification) as completed
8. **Proceed immediately** to the next step

## If You Get Stuck

When something isn't working as expected:
- First, make sure you've read and understood all the relevant code
- Consider if the codebase has evolved since the plan was written
- Make the best engineering decision, document it as a DEVIATION in the plan, and keep moving
- Only stop if the blocker is truly insurmountable (missing credentials, external dependency down)

Use sub-tasks sparingly - mainly for targeted debugging or exploring unfamiliar territory.

## Completion

After ALL steps are done:

1. Verify every task is marked completed
2. Do one final holistic codex review:
   ```
   mcp__clink__clink(
     cli_name: "codex",
     role: "codereviewer",
     prompt: "Final review of the complete implementation. The plan at [path] should now be fully executed. Review the entire implementation holistically — check for integration issues between steps, missing edge cases, and overall architecture quality. Verify SOLID, DRY, SRP, SSOT compliance across the whole.",
     absolute_file_paths: [all files changed during execution AND the plan document]
   )
   ```
3. Address any final feedback
4. Update the plan document with a completion summary at the top:
   ```markdown
   ## Execution Complete
   - **Completed**: [timestamp]
   - **Steps executed**: N/N
   - **Codex reviews**: M (all feedback addressed)
   - **Final review**: PASS
   ```

## Resuming Work

If the plan has existing checkmarks:
- Trust that completed work is done
- Pick up from the first unchecked item
- Verify previous work only if something seems off

Remember: You're implementing a solution, not just checking boxes. Keep the end goal in mind and maintain forward momentum.

---

## Agent Orchestration Mode

When implementing larger plans (4+ tasks), use agent orchestration to stay compaction-resistant.

### Why Agent Orchestration?

**The Problem:** During long implementations, context accumulates. If auto-compact triggers mid-task, you lose implementation context. Handoffs created at 80% context become stale.

**The Solution:** Delegate implementation to agents. Each agent:
- Starts with fresh context
- Implements one task
- Creates a handoff on completion
- Returns to orchestrator

Handoffs persist on disk. If compaction happens, you re-read handoffs and continue.

### Setup

1. **Create handoff directory:**
   ```bash
   mkdir -p agent-work/<session-name>
   ```
   Pick a short descriptive session name for the plan you're executing.

2. **Read the implementation agent skill:**
   ```bash
   cat $CLAUDE_CONFIG_DIR/skills/implement_task/SKILL.md
   ```
   This defines how agents should behave.

### Orchestration Loop

For each task in the plan:

1. **Prepare agent context:**
   - Read the plan (overall context)
   - Read previous handoff if exists (from agent-work/<session>/)
   - Identify the specific task

2. **Spawn implementation agent:**
   ```
   Task(
     subagent_type="general-purpose",
     model="opus",
     prompt="""
     [Paste contents of $CLAUDE_CONFIG_DIR/skills/implement_task/SKILL.md here]

     ---

     ## Your Context

     ### Plan:
     [Paste relevant plan section or full plan]

     ### Your Task:
     Task [N] of [Total]: [Task description from plan]

     ### Previous Handoff:
     [Paste previous task's handoff content, or "This is the first task - no previous handoff"]

     ### Handoff Directory:
     agent-work/<session-name>/

     ### Handoff Filename:
     task-[NN]-[short-description].md

     ---

     Implement your task and create your handoff.
     """
   )
   ```

3. **Process agent result:**
   - Read the agent's handoff file
   - Update plan checkbox if applicable
   - Continue to next task

4. **On agent failure/blocker:**
   - Read the handoff (status will be "blocked")
   - Present blocker to user
   - Decide: retry, skip, or ask user

### Recovery After Compaction

If auto-compact happens mid-orchestration:

1. List handoff directory:
   ```bash
   ls -la agent-work/<session-name>/
   ```
2. Read the last handoff to understand where you were
3. Continue spawning agents from next uncompleted task

### Example Orchestration Session

```
User: /implement_plan agent-work/add-auth/PLAN.md

Claude: I'll use agent orchestration for this plan (6 tasks).

Setting up handoff directory...
[Creates agent-work/add-auth/]

Task 1 of 6: Create user model
[Spawns agent with full context]
[Agent completes, creates task-01-user-model.md]

✅ Task 1 complete. Handoff: agent-work/add-auth/task-01-user-model.md

Task 2 of 6: Add authentication middleware
[Spawns agent with previous handoff]
[Agent completes, creates task-02-auth-middleware.md]

✅ Task 2 complete. Handoff: agent-work/add-auth/task-02-auth-middleware.md

--- AUTO COMPACT HAPPENS ---
[Context compressed, but handoffs persist]

Claude: [Reads ledger, sees tasks 1-2 done]
[Reads last handoff task-02-auth-middleware.md]

Resuming from Task 3 of 6: Create login endpoint
[Spawns agent]
...
```

### Handoff Chain

Each agent reads previous handoff → does work → creates next handoff:

```
task-01-user-model.md
    ↓ (read by agent 2)
task-02-auth-middleware.md
    ↓ (read by agent 3)
task-03-login-endpoint.md
    ↓ (read by agent 4)
...
```

The chain preserves context even across compactions.

### When to Use Agent Orchestration

| Scenario | Mode |
|----------|------|
| 1-3 simple tasks | Direct implementation |
| 4+ tasks | Agent orchestration |
| Critical context to preserve | Agent orchestration |
| Quick bug fix | Direct implementation |
| Major feature implementation | Agent orchestration |
| User explicitly requests | Respect user preference |

### Tips

- **Keep orchestrator thin:** Don't do implementation work yourself. Just manage agents.
- **Trust the handoffs:** Agents create detailed handoffs. Use them for context.
- **One agent per task:** Don't batch multiple tasks into one agent.
- **Sequential execution:** Start with sequential. Parallel adds complexity.
