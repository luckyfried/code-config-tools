# Repo Pulse

## What this makes

A dashboard of one repository's year, built from its own git history: a commit heat map with a card for every day
that lists its commits, a river of who committed month by month, a treemap of where the lines changed, the releases
as a strip of tags with the gaps in days, the busiest day called out, and the big numbers. Four screens: Overview,
Authors, Churn, and Timeline. Nothing calls GitHub; the page reads two files that git writes.

## Run

Run it once from the project folder before asking anything, so the person sees the sample year first:

```sh
cd <project> && cp -n <agent-apps root>/repo-pulse/inputs.example.json repo-pulse.inputs.json
cd <project> && python3 <agent-apps root>/repo-pulse/scripts/run.py
```

`run.py` reads `repo-pulse.inputs.json` in the project folder (the copy of `inputs.example.json` the first line
makes, when the person has none yet) and writes the page to `out/repo-pulse/`.

Then ask, in one message: "Which repository? How far back should it go? Any author names that are the same person?
Any paths to leave out of the churn map (lockfiles, generated code)?"

Export the repository's history beside the inputs file, from inside the repository:

```sh
cd <repository> && git log --all --date=iso-strict --numstat --format='%H%x09%an%x09%ad%x09%s' > <project>/repo-pulse.log
cd <repository> && git tag -l --format='%(refname:short)%09%(creatordate:iso-strict)' > <project>/repo-pulse.tags
```

Set `"logFile": "repo-pulse.log"` and `"tagsFile": "repo-pulse.tags"` in `repo-pulse.inputs.json`, fill in `title`,
`since`, `authorAliases`, and `ignorePaths` from the answers, and run `run.py` again. A missing or wrong key is named
in one line and the script exits 2; fix that key and run again.

## Check

`run.py` prints `Wrote out/repo-pulse/ (<n> files)`. Serve the folder (see Host) and open it: the heat map has one
cell per day from `since` to the newest commit, the header names the repository and the window, and hovering a day
(tapping, on a phone) lists that day's commits. The status chip reads "Sample year" only while the sample is showing.
`out/repo-pulse/data.js` holds everything the page draws.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/repo-pulse
```

and open `http://localhost:8000/`. Any static host serves `out/repo-pulse/` as it is, at any path. The page loads
`badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds; a tap opens Repo Pulse's page
on code-config.com. It sends no data, and removing its `<script src="./badge.js">` line from `index.html` removes it.

## Make it yours

Every key in `repo-pulse.inputs.json` changes the page with no build step; run `run.py` again after any change:

- `title`: the repository's name at the top of the page.
- `logFile`, `tagsFile`: the two exported files, relative to the inputs file. `null` shows the sample year.
- `since`: the first day to count, as `YYYY-MM-DD`; `null` counts the year up to the newest commit.
- `authorAliases`: `{ "name as git has it": "name to count it under" }`, to merge one person's several names.
- `ignorePaths`: lockfiles, vendored folders, and generated files to leave out of the churn map and the line counts.
  A file name or pattern (`pnpm-lock.yaml`, `*.min.js`) or a folder ending in `/` (`vendor/`).
- `theme`: `auto` follows the device's light or dark setting and shows a switch; `paper` is always light, with a blue
  ramp; `terminal` is always dark, with a green ramp and mono numerals.

A new theme is one more file in `site/themes/`: copy `paper.css`, change the token values (the ramp is `--heat-0` to
`--heat-5`, the authors are `--cat-1` to `--cat-8` and `--cat-rest`), and name it in `theme`. The layout lives in
`site/styles/`, the charts in `site/js/`; both are plain files the browser loads directly, with nothing to install.
