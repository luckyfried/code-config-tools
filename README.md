# Code Config tools

The tools [code-config.com](https://code-config.com) installs: skills, rules, output styles, hooks,
MCP configs, settings, and a statusline preset for coding agents. Plain files that work with Claude
Code, Codex, Muse, and GPT Dot.

## Layout

- `skills/`: one directory per skill. The directory name is the skill name and `SKILL.md` is its
  instructions.
- `rules/`: one Markdown file per rule.
- `output-styles/`: one Markdown file per style.
- `hooks/`: one directory per hook.
- `mcp-configs/`: one JSON file per group of MCP servers.
- `settings/`: one settings fragment per toolkit.
- `statusline/`: the statusline preset.

A skill adapted from another project carries that project's license in its own folder.

## License

MIT, see [LICENSE](LICENSE).
