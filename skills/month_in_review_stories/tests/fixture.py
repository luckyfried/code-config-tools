"""The fixture month as a user's agent gets it: the fixture's tables, photographs and pulled account copied into a fresh
workspace, then gather.py and research.py run there. month() returns month.json, build(ws) the run's build folder; the
workspace lives under TMPDIR."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SCRIPTS = KIT / "scripts"
FIXTURE = KIT / "evals" / "fixtures" / "september-recap"
sys.path.insert(0, str(SCRIPTS))

_month = None


def workspace():
    ws = Path(tempfile.mkdtemp(prefix="mir-test-"))
    shutil.copy2(FIXTURE / "posts.csv", ws / "posts.csv")
    shutil.copytree(FIXTURE / "pulled", ws / "pulled")
    shutil.copytree(FIXTURE / "photos", ws / "photos")
    return ws


def run(ws, script, *args):
    env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=ws, env=env, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(f"{script} {' '.join(args)} exited {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def researched(ws):
    """month.json from gather.py and research.py run in the workspace on the fixture's request, with each drafted
    moment's shot given the subject and the move the agent writes from its photograph."""
    run(ws, "gather.py", "--pulled", "pulled", "--month", (FIXTURE / "request.txt").read_text().split(" recap")[0].split()[-1])
    run(ws, "research.py")
    taste = json.loads((build(ws) / "taste.json").read_text())
    for x in taste["moments"]:
        x["shot"].update(subject=f"the {x['what']} in the photograph", move="a slow push in")
    (build(ws) / "taste.json").write_text(json.dumps(taste))
    return json.loads((build(ws) / "month.json").read_text())


def build(ws):
    return ws / "build" / (ws / "build" / "latest").read_text().strip()


def month():
    global _month
    if _month is None:
        _month = researched(workspace())
    return copy.deepcopy(_month)

