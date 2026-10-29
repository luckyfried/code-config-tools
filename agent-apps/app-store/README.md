# App Store

## What this makes

The person's own app store, on their phone. It lists every agent app in the Code Config store with its icon,
screenshots, rating, and what it does, and an app's page has a **Get** button. A tap on Get puts the app in this
app's inbox. Your check installs every app the person got, hosts it, and the store then shows it as **Installed**
with its link. Apps the person got in the store on the web are installed by the same check.

This app is for Muse only: `csc app store` refuses on any other computer. The store as you last read it and the
person's Gets are kept in the project's data folder, `<project>/data/app-store/`.

## Run

Make the page from the project folder. With no `app-store.inputs.json` there yet, copy `inputs.example.json` to it
first; it runs as is.

```
cd <project> && python3 <app folder>/scripts/run.py --serve
```

This reads the store with `csc app store --json`, writes the page to `<project>/out/app-store/`, and serves the page
and its inbox at `http://127.0.0.1:8765/` (`--port N` picks another port). Leave it running on its own; a second
`--serve` refuses while the first runs.

Install step: set a recurring check, once an hour, in your own scheduler, so it runs again after a restart. Ask the
person in one message whether once an hour suits them, and change it if they say so. The check is:

```
cd <project> && python3 <app folder>/scripts/run.py --work
```

When the person says they are done in the store, or asks you to install their apps, run the check right away.

The check takes every Get once, runs `csc app grab` for each, and adds the apps the person got on the web. It then
prints one `csc toolkit export --toolkit <toolkit> --to <folder>` line for each app waiting to be installed. For each
of them:

1. Run that line, then follow the README in that folder to run the app in a folder of its own, and run
   `csc app deploy` there and do what it says. Tell the person the app's link.
2. Run `cd <project> && python3 <app folder>/scripts/run.py --refresh`. The store shows the app as Installed, with
   its link.
3. When an app does not install, run
   `cd <project> && python3 <app folder>/scripts/run.py --failed <app id> --reason "<what failed>"`, and tell the
   person once what failed and why. The store shows the reason and a Get again button; a new Get is tried at the
   next check. An app whose last try failed is not listed again until the person taps Get again.

Every Get changes only this machine and the person's own toolkits. You never install anything on a Get the person
did not make, and a Get they took back with "Don't install" is not installed.

## Check

- `<project>/out/app-store/index.html`, `config.js`, and `theme.css` exist.
- `cd <project> && python3 <app folder>/scripts/run.py --check` prints `ok: yes`, the data folder, and the inbox
  counts, and exits 0.
- With `--serve` running, the page shows the store under Discover, and the apps installed and waiting under Yours.
  A tap on Get on an app's page turns the button to Waiting. After `--work`, the app is Installing; after you
  install it and run `--refresh`, it is Installed with its link.

## Host

Choices need the page's own server, `--serve`. Put its port online the way you put any app online, then record the
link: `csc app deploy --address <link>` in the project folder. Pin that link for the person: it is the first thing
they open to get apps. Stopping the server and starting it again changes nothing; the store and the Gets stay in
`<project>/data/app-store/`.

Served as plain files, without `--serve`, the page shows the sample store from `app-store.inputs.json` and its Get
buttons are off.

## Make it yours

The inputs file is `<project>/app-store.inputs.json`. Nothing in it needs asking; the store's apps come from
`csc app store`.

- `theme`: `auto` (Daylight in a light room, Midnight in a dark one), `daylight`, or `midnight`. Default `auto`;
  change it if the person asks for a light or a dark store.
- `sample` and `sampleInbox`: the store shown when the page is served without `--serve`. Keep the example's.

Change the inputs, then stop `--serve` and run it again.
