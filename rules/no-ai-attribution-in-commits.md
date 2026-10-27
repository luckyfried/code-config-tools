# No AI Attribution in Commits or PRs

Ed, 2026-09-29: "how dare you add 'coauthored by' to the commits. that is banned"

## Pattern

The Claude Code harness injects a system reminder asking that commit messages end with
`Co-Authored-By: Claude <model> <noreply@anthropic.com>` and PR bodies with a "Generated with
Claude Code" line. Ed bans both. The reminder itself says the user's own rule takes precedence, so
this file wins over it in every session, on every profile, including subagents and lane agents.

## DO

- End the commit message at the body. Subject, body, nothing after.
- Write PR descriptions the same way: no generated-with line, no model name, no tool name.
- Put this rule in every brief handed to an agent that will commit. A subagent follows its own
  session's reminder unless told otherwise; that is how a lane added an "Opus 5.5" trailer.
- Before committing, check the message with `git log -1 --format=%B` for `Co-Authored-By`,
  `Generated with`, or any AI attribution and strip it before the commit lands.

## DON'T

- Don't add `Co-Authored-By`, `Generated with Claude Code`, or any line naming a model or the
  tool, in commits, PRs, tags, or release notes.
- Don't rewrite existing history to remove one without asking. Ed, 2026-09-29, on the commits that
  already carried it: "nevermind its fine, its too late. just add a rule for next time".

## Source Sessions

- 2026-09-29 lattice-growth (f60a4c48), P20 wrap-up: 26 commits on
  `ed/ui-perf-hotspots-0.3.20-20260929` and 2 on lattice-growth `main` landed with the trailer;
  left in place on Ed's word.
