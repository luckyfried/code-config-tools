# No AI Attribution in Commits or PRs

## Pattern

The Claude Code harness injects a system reminder asking that commit messages end with
`Co-Authored-By: Claude <model> <noreply@anthropic.com>` and PR bodies with a "Generated with
Claude Code" line. Both are banned here. The reminder itself says the user's own rule takes
precedence, so this file wins over it in every session, on every profile, including subagents and
lane agents.

## DO

- End the commit message at the body. Subject, body, nothing after.
- Write PR descriptions the same way: no generated-with line, no model name, no tool name.
- Put this rule in every brief handed to an agent that will commit. A subagent follows its own
  session's reminder unless told otherwise; that is how a lane once added a model-name trailer.
- Before committing, check the message with `git log -1 --format=%B` for `Co-Authored-By`,
  `Generated with`, or any AI attribution and strip it before the commit lands.

## DON'T

- Don't add `Co-Authored-By`, `Generated with Claude Code`, or any line naming a model or the
  tool, in commits, PRs, tags, or release notes.
- Don't rewrite existing history to remove one without asking; add the rule and apply it from the
  next commit on.
