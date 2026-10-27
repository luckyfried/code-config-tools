# Code Config tools

Tools for coding agents: skills, rules, output styles, hooks, MCP configs, settings, and a
statusline preset. Plain files in the formats Claude Code, Codex, and Cursor read.

## Layout

`skills/` holds one directory per skill (the directory name is the skill name and `SKILL.md` is its
instructions), `rules/` one Markdown file per rule, `output-styles/` one Markdown file per style,
`hooks/` one directory per hook, `mcp-configs/` one JSON file per group of MCP servers, `settings/`
one settings fragment per toolkit, and `statusline/` the statusline preset. A skill adapted from
another project carries that project's license in its own folder.

## License

MIT, see [LICENSE](LICENSE).
