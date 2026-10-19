# Step 7: the critic, then fix the worst problem once

```
python3 S/scripts/qa.py check
```

Fix anything it marks FAIL first. Then spawn the critic as a sub-agent with the Agent tool (also called Task;
`subagent_type: "general-purpose"`), with this prompt, filled in:

```
You are the critic for an Instagram year-in-review video. Read S/critic/critic.md and follow it exactly.
Workspace root: <absolute path>. Skill folder: <absolute path of S>. This is round <N>.
The person asked: "<their exact words>".
```

When no Agent or Task tool exists, do it yourself: read `S/critic/critic.md` and follow it as written, opening
every frame before you score.

- Every score 4 or more: go to step 8.
- Any score under 4: make the one change the critic named for the worst problem (words in `build/story.json`, a
  chapter photo, or the accent), rebuild (`cards.py build`, `render.py --batch build/plan.json`, `motion.py`,
  `qa.py check`), and run round 2 with a fresh critic. Record the change with `--fixed "<what changed>"`.
- At most two rounds. Never edit `build/critic.json` by hand and never score your own work up.
