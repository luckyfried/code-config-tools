# Job Board

## What this makes

A board of the job openings you find for the person, in `out/job-board/`: one card per opening in the columns new,
yes, and later, which they sort with a tap, a swipe on a phone, or the keys Y, N, and L on a desktop. Their choices
come back to you through the app's inbox, and the openings and choices are kept in `<project>/data/job-board/`.

## Run

Make the page first, before asking for anything personal. Copy `inputs.example.json` to `job-board.inputs.json` in
the project folder if it is not there, then run:

```sh
cd <project> && python3 <agent-apps folder>/job-board/scripts/run.py --serve --port 8000
```

That writes the page to `out/job-board/` and serves it, with the inbox, at `http://127.0.0.1:8000/` until stopped.
Without `--serve` it only writes the page. The board's openings, the person's choices, and the server's process id
live in the data folder, `<project>/data/job-board/`, which the first run makes.

How you work the board, each from the project folder:

1. **Add what you found.** Write the openings as a JSON list in a file (each with `id`, `role`, `company`, `link`,
   `location`, `pay`, `remote` as true, false, or null, `facts` and `agent_notes` as lists of sentences, and
   `found_at` as a time), then run `python3 <agent-apps folder>/job-board/scripts/run.py --add <file>`. An id that is
   already on the board updates that opening at its current revision; give `"revision"` with the number you last
   read, and a person's change since then is refused with a line naming it, so nothing is overwritten. The page
   shows new openings within five seconds.
2. **Read the person's choices** when they ask you to: run `python3 <agent-apps folder>/job-board/scripts/run.py
   --work`. It takes every waiting choice once and prints one line for each. A yes, no, or later moves the opening and
   prints the move. An apply prints `Ask before: apply to <role> at <company> (<link>)`.
3. **Apply only after asking.** A choice on the page never reaches outside this computer. For each `Ask before:`
   line, ask the person in the conversation, and apply only once they say so.
4. **Record each application you send.** Once it has gone out, run `--add` with a file holding
   `[{"id": "<the opening's id>", "applied_at": "<the time it went out>"}]`. The card then says Applied with a check;
   until then an apply says Applying… while it waits for `--work` and With your agent after.

## Check

- `out/job-board/index.html`, `out/job-board/config.js`, and `out/job-board/theme.css` exist, and `config.js` holds the
  person's name and ask.
- `python3 <agent-apps folder>/job-board/scripts/run.py --check`, run from the project folder, prints the data folder,
  the inbox counts, and `ok: yes`, and exits 0.
- With `--serve` running, `http://127.0.0.1:8000/` shows the person's name in the title, their openings in their
  columns, and a choice made there appears in `<project>/data/job-board/inbox/`.

## Host

On this computer, `--serve` keeps the board and its inbox running for as long as the command runs; stop it with
Ctrl+C or by its process id in `<project>/data/job-board/server.pid`. Choices need `--serve`. The page alone, with
the sample openings and the choices turned off, also runs from any static host: serve the folder with
`cd <project> && python3 -m http.server 8000 --directory out/job-board`, or copy `out/job-board/` to a static host the
person names. For a cloud agent, put the output folder `out/job-board` online.

## Make it yours

Ask for the personal things in one message: the person's first name, what they are looking for, and the look.
These keys in `<project>/job-board.inputs.json` need no Node, only another run:

- `name`: their first name; the board's title is "<name>'s job board". Ask for it.
- `ask`: what they are looking for, in one sentence, shown at the top. Ask for it.
- `columns`: which columns a desktop shows, from `new`, `yes`, `later`, and `no`; without `no`, passed openings are a
  count in the status line that shows them on a tap. Default `["new", "yes", "later"]`.
- `theme`: `auto` follows the device between the two looks, `paper` is index cards on a kraft desk, `night` is a cool
  slate board. Default `auto`.
- `sample`: the openings the page shows before `--serve` runs. Default the ten in `inputs.example.json`.
- `sampleInbox`: choices the sample shows, each with `action`, `target`, `status`, and `at`. Optional.

The words on the board come from these keys (the title, the ask, and every opening), and the colors come from
`src/themes/<name>.css`, which `run.py` copies, so neither needs Node. A new component, a change to a page, or a new
dependency needs Node, in two folders in this order: edit `src/`, run `cd <agent-apps folder>/job-board && npm ci && npm run build`
in the app folder, then run the Run command above from the project folder.
