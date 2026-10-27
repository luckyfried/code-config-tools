# Code Config tools

Portable tooling for coding agents: skills, rules, output styles, hooks, MCP configs, and a
statusline preset that work across Claude Code, Codex, Cursor, and anything else that reads these
formats.

Nothing here is a framework. Each piece is a plain file you can copy into your own agent config, or
install as part of a toolkit from [code-config.com](https://code-config.com), which installs each
piece and the configuration it needs as one unit.

## Layout

`skills/` holds one directory per skill, `rules/` one Markdown file per rule, `output-styles/` one
Markdown file per style, `hooks/` one directory per hook bundle, `mcp-configs/` one JSON file per
group of MCP servers, `settings/` one settings fragment per toolkit, and `statusline/` the
ccstatusline preset. Each directory carries its own `AGENTS.md` describing how to work in it;
`CLAUDE.md` is a one-line `@AGENTS.md` import of it.

## The layout is a contract

**A skill is a directory that directly contains `SKILL.md`.** The directory name is the skill name
and how it's invoked (`skills/fanout-codex/` → `/fanout-codex`). Everything under that directory
belongs to that skill: helper scripts, `references/`, and its settings.

**A `settings.json` beside a `SKILL.md` carries the host settings that skill works best with.** The
file is a settings fragment in the host's own schema, for Claude Code a partial `settings.json`, so
it merges as an overlay. A skill that needs no settings has no `settings.json` at all. Claude Code
does not read these files itself; they exist so the setting travels with the skill and both are
applied together at install time.

**An MCP config in `mcp-configs/` is installed with the skills that use it.** `clink.json` declares
**clink**, which the `fanout-*` skills, `implement_plan`, and `codex-review` drive: it hands a prompt
to another coding app on your computer and returns its answer, Codex, Claude, or Claude pointed at
Kimi or Z.ai. The app it starts signs in with one of your Code Config logins that still has usage
left and carries the same toolkit as the session that asked, so it reaches the same tools and
project. It runs through `csc`, which the Code Config installer puts on your PATH; nothing else to
install. macOS, Linux and Windows.

## What the skills pair with

A skill installs on its own. The tools below are what a skill is for, not a step before it:

- **Unreal Engine 5.8**: the `ue-*` skills. They pair with community skills that cover the rest of
  the engine and name them where the topics meet:
  [quodsoler/unreal-engine-skills](https://github.com/quodsoler/unreal-engine-skills),
  [JetBrains/rider-skills](https://github.com/JetBrains/rider-skills), the `unreal-mcp`,
  `create-toolset` and `unreal-skill` skills from
  [EpicGames/unreal-engine-skills-for-claude-code-plugin](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin),
  `unreal-pcg-python` from [maystudios/claude-skills](https://github.com/maystudios/claude-skills),
  `renderdoc-gpu-debug` from [rudybear/renderdoc-skill](https://github.com/rudybear/renderdoc-skill)
  and `cli-anything-unrealinsights` from [HKUDS/cli-anything](https://github.com/HKUDS/cli-anything).
  `mcp-configs/unreal-profiling.json` declares the two profiling servers `ue-profiling-workflow`
  uses: **ue-trace** reads Unreal Insights `.utrace` files (runs through `npx`; Windows and Linux),
  and **tracy** connects to the [Tracy](https://github.com/wolfpld/tracy) profiler's MCP server at
  `http://127.0.0.1:47380/mcp`, started from your Tracy checkout with `extra/mcp/start_mcp.sh`.
- **Three.js**: `threejs-current-api` and `threejs-visual-check` pair with
  [CloudAI-X/threejs-skills](https://github.com/CloudAI-X/threejs-skills),
  [OpenAEC-Foundation/Three.js-Claude-Skill-Package](https://github.com/OpenAEC-Foundation/Three.js-Claude-Skill-Package),
  [EnzeD/r3f-skills](https://github.com/EnzeD/r3f-skills),
  [dgreenheck/webgpu-claude-skill](https://github.com/dgreenheck/webgpu-claude-skill),
  [linegel/threejs-complete-set-of-skill](https://github.com/linegel/threejs-complete-set-of-skill),
  [majidmanzarpour/threejs-game-skills](https://github.com/majidmanzarpour/threejs-game-skills)
  and the `gltf-transform` skill from [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD).
  `mcp-configs/threejs.json` declares **threejs-devtools** (reads and edits a running scene through
  `npx`), **chrome-devtools** (Google's Chrome DevTools server; needs Chrome), and **pmndrs-docs**
  (hosted documentation for React Three Fiber, Drei, Zustand and React Postprocessing).
- **Unity 6**: the `unity-*` skills. They pair with Unity's official skills and name them where the
  topics meet, such as `unity-cli`, `ui-uitk` and `setup-multiplayer-services`. Unity's skills are
  under the Unity Companion License and are not included here; install them from Unity with its
  [`unity` plugin](https://github.com/Unity-Technologies/unity-agent-plugin) for Claude Code or
  Codex (`unity-compile-and-test` lists the commands). Also paired: `unity-ecs-patterns` from
  [wshobson/agents](https://github.com/wshobson/agents) and `renderdoc-gpu-debug` from
  [rudybear/renderdoc-skill](https://github.com/rudybear/renderdoc-skill). The editor connection is
  Unity's own MCP server (`unity mcp` in the [Unity CLI](https://docs.unity.com/en-us/unity-cli/unity-cli));
  `unity-compile-and-test` covers setting it up. `unity-2d`, `unity-addressables`,
  `unity-animation`, `unity-editor-tools`, `unity-multiplayer`, `unity-perf-audit`, `unity-save`,
  `unity-shader-gen` and `unity-test` are adapted from
  [JulianKerignard/Unity-Skills](https://github.com/JulianKerignard/Unity-Skills) under its MIT
  license, which each folder carries in its own `LICENSE`.
- **Blender 5.x**: the `blender-*` skills. The editor connection is Blender's official MCP server
  ([Blender Lab](https://www.blender.org/lab/mcp-server/), also the Blender connector in Claude's
  connector directory; Blender 5.1 or newer). `blender-verify` covers setting it up and a headless
  `blender -b` fallback. The skills pair with
  [ra100/blender-claude-plugin](https://github.com/ra100/blender-claude-plugin),
  `blender-image-to-3d` from [donth77/blender-game-skills](https://github.com/donth77/blender-game-skills)
  and the `gltf-transform` skill from [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD).
  `blender-animation-rigging` and `blender-compositing-nodes` are adapted from
  [ra100/blender-claude-plugin](https://github.com/ra100/blender-claude-plugin) under its MIT
  license, which each folder carries in its own `LICENSE`.
- **ComfyUI**: the `comfyui-*` skills drive ComfyUI through Comfy Org's official MCP servers, the
  local [comfy-mcp](https://github.com/Comfy-Org/comfy-mcp) (`pip install comfy-mcp "comfy-cli>=1.14.0"`,
  then `comfy launch`) or Comfy Cloud; `comfyui-setup-and-verify` covers both. They pair with
  [jtydhr88/comfyui-custom-node-skills](https://github.com/jtydhr88/comfyui-custom-node-skills),
  `comfyui-prompt-interview` from [MCKRUZ/ComfyUI-Expert](https://github.com/MCKRUZ/ComfyUI-Expert)
  and the `comfy-cloud` commands from [Comfy-Org/comfy-skills](https://github.com/Comfy-Org/comfy-skills).
  `mcp-configs/comfyui.json` declares **comfy-cloud**, Comfy Org's hosted server; it signs in with
  your Comfy account, searching is free and generating needs a Comfy Cloud subscription.
  `comfyui-api`, `comfyui-prompt-engineer` and `comfyui-troubleshooter` are adapted from
  [MCKRUZ/ComfyUI-Expert](https://github.com/MCKRUZ/ComfyUI-Expert) under its MIT license, which
  each folder carries in its own `LICENSE`.
- **ccstatusline**: `statusline/` is a preset for
  [ccstatusline](https://www.npmjs.com/package/ccstatusline), run through `npx`; see
  `statusline/README.md`.
- **A `/goal` command**: `create-goal` scaffolds a goal under `thoughts/shared/goals/` in the
  target project and hands back the prompt you pass to the `/goal` command Claude Code and Codex
  each ship.

## License

MIT, see [LICENSE](LICENSE).
