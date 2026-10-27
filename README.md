# Code Config tools

Skills, rules, output styles, hooks, MCP configs, settings, and a statusline preset for coding
agents. Plain files that work with Claude Code, Codex, and Cursor.

## Layout

`skills/` holds one directory per skill (the directory name is the skill name and `SKILL.md` is its
instructions), `rules/` one Markdown file per rule, `output-styles/` one Markdown file per style,
`hooks/` one directory per hook, `mcp-configs/` one JSON file per group of MCP servers, `settings/`
one settings fragment per toolkit, and `statusline/` the statusline preset. A skill adapted from
another project carries that project's license in its own folder.

## License

MIT, see [LICENSE](LICENSE).
