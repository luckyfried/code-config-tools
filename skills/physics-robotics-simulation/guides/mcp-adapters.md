# MCP servers: what the toolkit adds and how to use them safely

Every result this kit verifies comes from scripts (`simulate.py`, `bundle.py`, `blender -b`
scripts, `wasm/rollout.mjs`). MCP servers are for looking at and steering a live session. Treat
anything an MCP tool reports as a lead to confirm with a script, never as the measurement.

## No isolation: read this first

The app starts each MCP server as an ordinary process with your user's permissions. It does not
put it in a container or a sandbox, and it does not limit its files or its network. An MCP server
can do whatever you can do on this computer. The checks below are the whole of the protection, and
you (or your agent) apply them.

## Playwright MCP (`@playwright/mcp`, pinned)

Used to drive the browser preview (`wasm/serve.mjs`): open `http://127.0.0.1:8765/`, read
`window.__preview` (time, contacts, heap size, errors), press play, pause, reset and reload,
take screenshots. It only needs the local preview address; do not point it at other sites from
this toolkit's work.

## Blender MCP (`mcp-for-blender`, PyPI, pinned)

A community server (MIT) that talks to an add-on running inside an open Blender. It is not the
Blender project's own MCP server; `blender-verify` describes that one separately. What it does,
read from the pinned release's source:

- The add-on listens on `localhost:9876` with no authentication. Any program on this computer
  that connects can send it Python, and the add-on runs it inside Blender with `exec`.
- Its `execute_blender_code` tool runs any Python the agent writes. With
  `BLENDER_MCP_SAFE_MODE=1` (set in this toolkit) the server checks that code first: only `bpy`,
  `bmesh`, `mathutils` and plain standard-library imports, no `eval`/`exec`/`open`, no
  `os`/`subprocess`/network, no handlers, timers or drivers. That check runs in the MCP server
  only; the add-on's socket itself still accepts anything. It is a guard rail, not a sandbox.
- Data collection (prompts, generated code, viewport screenshots) is off unless you opt in;
  this toolkit also sets `DISABLE_TELEMETRY=true`, which turns it off whatever the add-on says.
- Remote asset services (Poly Haven, Sketchfab, Hyper3D Rodin, Hunyuan3D, Tripo, Poly Pizza) are
  check boxes in the add-on's panel, all off by default. Leave them off for this work.

### Qualification checklist before you connect it

Work through this once per computer, and again after any upgrade:

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for the `uvx` command,
   then install the add-on from the same release the toolkit pins:
   `uvx mcp-for-blender@2.1.9 install-addon`, then enable "MCP for Blender" in Blender's
   Preferences > Add-ons and restart Blender. A newer add-on than the server, or an older one, is
   a mismatch; the server's `get_addon_status` tool reports it.
2. Open only Blender files you trust while the add-on's server is running; a `.blend` can carry
   its own scripts, and the add-on gives anything local a way in.
3. Never forward or expose port 9876 (no ssh `-R`/`-L` to it, no container port mapping, no
   tunnel). It must only ever be reachable from this computer.
4. Confirm the toolkit's settings reached the server: in the MCP entry, `DISABLE_TELEMETRY=true`,
   `BLENDER_MCP_SAFE_MODE=1`, `BLENDER_HOST=127.0.0.1`.
5. In the add-on panel, confirm every remote asset service is unchecked and data collection is
   off.
6. The add-on starts its server whenever Blender opens ("Auto-Start Server" is on by default), so
   every Blender session with the add-on enabled is listening. Uncheck "Auto-Start Server" in its
   panel, press "Connect to MCP server" only while you use it, and "Disconnect" when you are done.
   The kit's batch scripts run Blender with `--factory-startup`, which loads no add-ons, so they
   never open the port.
7. Do the real work through `blender -b` scripts. Use the MCP connection to look, to try a pose,
   to take a viewport screenshot; then write what worked into a script and rerun it in batch.

The add-on refuses to start in `blender -b`: Blender's UI event loop must be running to execute
commands. On a Linux server, install Xvfb (`apt install xvfb xauth`) and run
`xvfb-run -a blender` without `-b`, with the add-on enabled. Batch scripts still use `-b` directly.

## MuJoCo MCP (community, optional, not part of the toolkit)

`Rongxuan-Zhou/mujoco-mcp-server` (MIT) wraps a MuJoCo session as MCP tools. It is not published
as a versioned package, so the toolkit cannot add it for you; the Python scripts in this kit run
simulations without it. If you want it anyway, install it yourself from one reviewed commit:

1. Read the code at the commit you install. The one reviewed for this kit is
   `ce9bed80ec3698d7b778230abc21f2228a3ce94b`; anything newer needs its own read.
2. Install that commit into its own virtual environment, never your kit environment:
   ```
   python -m venv ~/mujoco-mcp-venv
   ~/mujoco-mcp-venv/bin/pip install "git+https://github.com/Rongxuan-Zhou/mujoco-mcp-server@ce9bed80ec3698d7b778230abc21f2228a3ce94b"
   ```
3. Run it over stdio only (`~/mujoco-mcp-venv/bin/mujoco-mcp`, the default). Its HTTP mode
   listens on every network interface (`0.0.0.0:8080`) with no authentication; never start it
   that way.
4. Pin its `mujoco` to the kit's version (`pip install mujoco==3.17.0` in that environment) so
   its numbers can be compared with `simulate.py`.
5. Add it to your coding app's own MCP settings as a stdio server pointing at that executable.
   It is your install: the toolkit does not manage, update or remove it.

## Remote services

Nothing in this toolkit sends your models, renders or screenshots to a remote service. Keep it
that way: no remote vision tools, no remote asset services, no data collection.
