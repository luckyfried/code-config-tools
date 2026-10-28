"""Repo Pulse: turns one repository's exported git log into a served dashboard.

Run from the project folder:

    python3 <agent-apps root>/repo-pulse/scripts/run.py

It reads repo-pulse.inputs.json from the current folder, streams the git log
and the tag list that file names (or the sample year that ships with the app),
aggregates commits per day, per author per month, per week, and lines changed
per directory, and writes out/repo-pulse/ with config.js, theme.css, and
data.js beside the page. Standard library only; two runs on the same inputs
write the same bytes.
"""

import fnmatch
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

SLUG = "repo-pulse"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
SAMPLE = APP / "sample"
INPUTS = f"{SLUG}.inputs.json"

KEYS = {
    "title": (str,),
    "logFile": (str, type(None)),
    "tagsFile": (str, type(None)),
    "since": (str, type(None)),
    "authorAliases": (dict,),
    "ignorePaths": (list,),
    "theme": (str,),
}
TYPE_WORDS = {
    "title": "text",
    "logFile": "a file name or null",
    "tagsFile": "a file name or null",
    "since": "a date like 2025-11-01, or null",
    "authorAliases": "an object of names",
    "ignorePaths": "a list of paths",
    "theme": "a theme name",
}

TOP_AUTHORS = 8
TREE_DEPTH = 4
TREE_CHILDREN = 14
SUBJECTS_PER_DAY = 6
SUBJECT_CHARS = 110
TOP_FILES = 10

HEADER = re.compile(r"^([0-9a-f]{40})(?:\t|%x09)(.*?)(?:\t|%x09)(\d{4}-\d{2}-\d{2})T\S*(?:\t|%x09)(.*)$")
NUMSTAT = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
TAG = re.compile(r"^(.+?)(?:\t|%x09|%09)(\d{4}-\d{2}-\d{2})")
BRACE_RENAME = re.compile(r"\{([^{}]*) => ([^{}]*)\}")


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def read_inputs(project):
    path = project / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON ({error})."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} should hold one object of keys."])
    problems = []
    for key, types in KEYS.items():
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
        elif not isinstance(inputs[key], types) or isinstance(inputs[key], bool):
            problems.append(f'{INPUTS} has "{key}" as the wrong type; it should be {TYPE_WORDS[key]}.')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')
    if isinstance(inputs.get("since"), str):
        try:
            date.fromisoformat(inputs["since"])
        except ValueError:
            problems.append(f'{INPUTS} has "since" as "{inputs["since"]}"; it should be a date like 2025-11-01.')
    aliases = inputs.get("authorAliases")
    if isinstance(aliases, dict) and not all(isinstance(v, str) for v in aliases.values()):
        problems.append(f'{INPUTS} has "authorAliases" with a value that is not a name.')
    ignore = inputs.get("ignorePaths")
    if isinstance(ignore, list) and not all(isinstance(v, str) for v in ignore):
        problems.append(f'{INPUTS} has "ignorePaths" with an entry that is not a path.')
    if isinstance(inputs.get("theme"), str):
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS} has "theme" as "{inputs["theme"]}"; the themes are {", ".join(names)}.')
    if problems:
        fail(problems)
    return inputs


def source_file(project, inputs, key, sample_name):
    name = inputs[key]
    if name is None:
        return SAMPLE / sample_name, True
    path = (project / name).resolve()
    if not path.is_file():
        fail([f'{INPUTS} names "{name}" as {key}, and there is no such file beside it.'])
    return path, False


def real_path(path):
    """The path a numstat line ends at, after a rename."""
    if " => " not in path:
        return path
    if "{" in path:
        path = BRACE_RENAME.sub(lambda m: m.group(2), path)
        return re.sub(r"/{2,}", "/", path).strip("/")
    return path.split(" => ", 1)[1]


def ignored(path, patterns):
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern) or f"/{pattern}" in f"/{path}":
                return True
        elif fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], pattern):
            return True
    return False


def stream_commits(path):
    """Each commit as (sha, author, day, subject, [(added, removed, path)]), read line by line."""
    current = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n").rstrip("\r")
            head = HEADER.match(line)
            if head:
                if current:
                    yield current
                current = (head.group(1), head.group(2), head.group(3), head.group(4), [])
                continue
            stat = NUMSTAT.match(line)
            if stat and current:
                added = 0 if stat.group(1) == "-" else int(stat.group(1))
                removed = 0 if stat.group(2) == "-" else int(stat.group(2))
                current[4].append((added, removed, real_path(stat.group(3))))
    if current:
        yield current


def week_start(day):
    return day - timedelta(days=day.weekday())


def month_key(day):
    return f"{day.year:04d}-{day.month:02d}"


def months_between(first, last):
    out = []
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def build_tree(lines_by_path):
    root = {}
    for path, size in lines_by_path.items():
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1]] = node.get(parts[-1], 0) + size
    return root


def tree_size(node):
    return node if isinstance(node, int) else sum(tree_size(v) for v in node.values())


def shape_tree(name, node, depth):
    """A directory as {n, s, c}: name, lines, and children by size, the smallest folded into one."""
    if isinstance(node, int):
        return {"n": name, "s": node}
    size = tree_size(node)
    out = {"n": name.rstrip("/"), "s": size, "d": 1}
    if depth >= TREE_DEPTH:
        return out
    kids = sorted(node.items(), key=lambda kv: (-tree_size(kv[1]), kv[0]))
    kids = [kv for kv in kids if tree_size(kv[1]) > 0]
    shown = kids[:TREE_CHILDREN]
    rest = kids[TREE_CHILDREN:]
    out["c"] = [shape_tree(k, v, depth + 1) for k, v in shown]
    if rest:
        out["c"].append({"n": f"{len(rest)} more", "s": sum(tree_size(v) for _, v in rest), "r": len(rest)})
    return out


def aggregate(inputs, log_path, tags_path, sample):
    aliases = inputs["authorAliases"]
    patterns = inputs["ignorePaths"]
    since = date.fromisoformat(inputs["since"]) if inputs["since"] else None

    per_day = Counter()
    day_subjects = defaultdict(list)
    author_commits = Counter()
    author_lines = defaultdict(lambda: [0, 0])
    author_days = defaultdict(set)
    author_month = defaultdict(Counter)
    author_first = {}
    author_last = {}
    lines_by_path = Counter()
    commits_by_path = Counter()
    added_total = removed_total = ignored_total = 0
    commits = 0
    first_day = last_day = None
    kept = []

    # The window ends at the newest commit; with no since, it opens one year before it.
    newest = oldest = None
    for _, _, day, _, _ in stream_commits(log_path):
        d = date.fromisoformat(day)
        newest = d if newest is None or d > newest else newest
        oldest = d if oldest is None or d < oldest else oldest
    if newest is None:
        fail([f"The log file named in {INPUTS} holds no commits; run the README's git command again."])
    if since is None:
        since = newest - timedelta(days=364)

    for sha, author, day, subject, stats in stream_commits(log_path):
        d = date.fromisoformat(day)
        if d < since:
            continue
        author = aliases.get(author, author).strip() or "Unknown"
        commits += 1
        first_day = d if first_day is None or d < first_day else first_day
        last_day = d if last_day is None or d > last_day else last_day
        per_day[d] += 1
        author_commits[author] += 1
        author_days[author].add(d)
        author_month[author][month_key(d)] += 1
        author_first[author] = min(author_first.get(author, d), d)
        author_last[author] = max(author_last.get(author, d), d)
        kept.append((d, sha[:7], author, subject[:SUBJECT_CHARS]))
        for added, removed, path in stats:
            if ignored(path, patterns):
                ignored_total += added + removed
                continue
            added_total += added
            removed_total += removed
            author_lines[author][0] += added
            author_lines[author][1] += removed
            lines_by_path[path] += added + removed
            commits_by_path[path] += 1

    if commits == 0:
        fail([f"The log has no commits on or after {since.isoformat()}; set an earlier since in {INPUTS}."])

    start = max(since, oldest)
    end = last_day
    n_days = (end - start).days + 1
    days = [per_day.get(start + timedelta(days=i), 0) for i in range(n_days)]

    ranked = sorted(author_commits, key=lambda a: (-author_commits[a], a))
    index = {a: i for i, a in enumerate(ranked)}
    for d, short, author, subject in kept:
        bucket = day_subjects[(d - start).days]
        if len(bucket) < SUBJECTS_PER_DAY:
            bucket.append([short, index[author], subject])

    months = months_between(start, end)
    top = ranked[:TOP_AUTHORS]
    river = [[author_month[a].get(m, 0) for m in months] for a in top]
    rest = [sum(author_month[a].get(m, 0) for a in ranked[TOP_AUTHORS:]) for m in months]

    weeks_start = week_start(start)
    n_weeks = (week_start(end) - weeks_start).days // 7 + 1
    weeks = [0] * n_weeks
    for i, count in enumerate(days):
        if count:
            weeks[((start + timedelta(days=i)) - weeks_start).days // 7] += count

    tags = []
    if tags_path is not None:
        with tags_path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                m = TAG.match(raw.strip())
                if not m:
                    continue
                d = date.fromisoformat(m.group(2))
                if start <= d <= end:
                    tags.append([m.group(1).strip(), (d - start).days])
    tags.sort(key=lambda t: (t[1], t[0]))

    busiest = max(range(n_days), key=lambda i: (days[i], -i))
    streak = best = 0
    for count in days:
        streak = streak + 1 if count else 0
        best = max(best, streak)

    tree = shape_tree("", build_tree(lines_by_path), 0)
    top_files = sorted(lines_by_path, key=lambda p: (-lines_by_path[p], p))[:TOP_FILES]

    authors = [
        {
            "n": a,
            "c": author_commits[a],
            "a": author_lines[a][0],
            "r": author_lines[a][1],
            "d": len(author_days[a]),
            "f": (author_first[a] - start).days,
            "l": (author_last[a] - start).days,
        }
        for a in ranked
    ]

    return {
        "title": inputs["title"],
        "sample": sample,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "commits": commits,
        "added": added_total,
        "removed": removed_total,
        "ignored": ignored_total,
        "activeDays": sum(1 for c in days if c),
        "streak": best,
        "busiest": busiest,
        "days": days,
        "subjects": {str(k): v for k, v in sorted(day_subjects.items())},
        "authors": authors,
        "months": months,
        "river": river,
        "rest": rest,
        "weekStart": weeks_start.isoformat(),
        "weeks": weeks,
        "tags": tags,
        "tree": tree,
        "files": [[p, lines_by_path[p], commits_by_path[p]] for p in top_files],
    }


def main():
    project = Path.cwd()
    inputs = read_inputs(project)
    log_path, sample = source_file(project, inputs, "logFile", "repo-pulse.log")
    if inputs["tagsFile"] is None:
        tags_path = SAMPLE / "repo-pulse.tags" if sample else None
    else:
        tags_path, _ = source_file(project, inputs, "tagsFile", "repo-pulse.tags")

    data = aggregate(inputs, log_path, tags_path, sample)

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    if (APP / "badge.js").is_file():
        shutil.copyfile(APP / "badge.js", out / "badge.js")
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )
    (out / "data.js").write_text(
        f"window.__REPO_PULSE__ = {json.dumps(data, ensure_ascii=False, separators=(',', ':'))};\n",
        encoding="utf-8",
    )
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
