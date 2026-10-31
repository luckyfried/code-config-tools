# 0. Gather: the subject, the person's photographs, then anything and everything you already have access to

Goal: a new run folder (`build/<run stamp>/`, named by `build/current`) holding `library.json`: the subject as the
person gave it (who or what it is, its own words and pictures, a date when it is a launch), the feed the films are
cast from (their photographs, each with its caption and date), and every post, reel, story, caption, like, save,
comment and follow of theirs you can reach. More sources are better. Nothing you can already reach is off limits.

## Ideas first, when the request names no subject

When the request names no subject, or only a vague one ("make me a hype reel", "hype something up", "what could you
make for me", "give me ideas for a reel"), the first thing is to offer ideas. Pull what the doors below give (their
connected account, a signed-in browser) into `pulled/items.json` first, then run:

```
python3 S/scripts/ideas.py [--pulled pulled] [--most 4]
```

It drafts three to five ideas, one plain line each, each naming a subject and an angle ("your friend @ines and the
food you share, played as a movie trailer"), from what the kit can reach: what they post and save most, the accounts
and creators they follow, the friend they talk with most in comments, a project of theirs in the workspace, and one
they did not think of. It writes `build/ideas.json` and prints the ideas numbered with "Something else" last.

Offer them as clickable options: where the session has AskUserQuestion, one call with the ideas as its options (four fit;
"Something else" is the tool's own free-text answer); anywhere else, the numbered list as printed. This is the first
of the kit's two questions; the second is the look, in movement 3. The picked idea's subject goes into `--subject`
and `--kind` below, and its tone into `taste.json` `plan.tone` in movement 1. When they answer "something else",
their answer is the subject.

An idea names only what the person can see themselves. Anything private read while drafting (a message, a private
account's posts) appears on screen or in a caption only when the person picked the idea it came from; `ideas.json`
marks such an idea `private`. A request that names its subject skips this step entirely.

## The subject, from the request

Take these from what the person wrote, in their words:

- **the subject**: who or what the reel hypes, its name as they wrote it: a product, a drop or event, a friend, an
  idea, or a thing they follow (an account, a creator, a band, a place, a repo, a page);
- **what it is** (`--kind`): one word, product, drop, event, friend, idea, account, creator, band, place, repo, page or
  thing;
- **what they know about it**: write it into a `subject.md` beside its pictures (`# Name`, a `kind:` line, a `handle:`
  line, one `- ` line per true fact in their words or the subject's own, and a `## page` section holding text saved
  from the subject's page), and pass it as `--about`. A page you can open (a profile, a repo, a shop) is read and its
  text saved there; never invent a fact, a number or a quote;
- **the pictures**: the folder or the link they named (`--assets`), else the pictures beside `subject.md`. A link is
  passed as it is; gather.py downloads the page's images. One picture is enough;
- **a date, only when there is one**: a launch, a drop or an event with a day (`--date`, as they wrote it), or a launch
  with no day yet (`--launch`). Only then are the teaser stories and the countdown card made. A day with no month
  ("the 14th") or a weekday alone goes in as written, and gather reads it as the next such day and records that as an
  assumption.

Whatever they did not name, leave out: gather.py infers it (the name from the posts that repeat it, a folder named
like the subject, else their own posts about it) and lists the inference as an assumption in `brief.md`.

## The feed: the photographs the films are cast from

Pass every folder of the person's own photographs you have as `--feed DIR` (repeatable): their camera roll first, a
folder they named, the media you pulled from their account. A photograph's entry in a `manifest.json` beside it
(`{"items": [{"file", "caption", "title", "description"}]}`) holds their own words in `caption` (the post's caption, the
note they wrote with it, word for word, or empty) and what the photograph shows in `title` and `description`; else a
`.txt` file of the same name holds their words; else the words of its file name say what it shows. Write that file
for what you pulled. Their words are what the film says over the photograph; the title and description are how the
cast reads what it shows. Its date comes from its EXIF. Look at every photograph of a folder whose words are missing
or say something the picture does not show, and write its title and description from what you see; never write their
`caption` for them. Without `--feed` the feed is the photographs of their posts, with each post's caption and day.

`library.json` `settings` records what the storyboards read: `feed_photos` (the feed folders) and `subject_assets`
(the subject folder). A feed with none makes the films from the subject alone.

## Try every door, in this order, and write down what each one gave

1. **Their connected Instagram or Facebook account.** If you have an Instagram or Facebook tool, pull the year: posts
   (caption, date, likes, comments, saves, place, media), reels, stories and highlights, likes and saves, the
   comments they wrote, followers and following (mark an account they follow that is private with `"private": true`),
   insights when present. Save the media files under `pulled/` and write `pulled/items.json` in the shape
   `gather.py --help` prints.
2. **A browser that is already signed in.** If you have a browser tool and it is signed in to Instagram or
   Facebook, open their profile, scroll the year, and save what you can the same way.
3. **A "Download your information" export** anywhere under the workspace (a folder or a `.zip`): gather.py finds it.
4. **A folder of photos and clips they named** in the request: pass it as `--feed DIR` and as `--photos DIR` (the
   subject's pictures go in `--assets`, never here).
5. **The largest folder of images under the workspace**: gather.py falls back to it on its own.

## Run

```
python3 S/scripts/gather.py --subject '<name>' --kind <word> [--about <folder>/subject.md] [--assets '<folder or link>'] \
  [--date '<date as written>' | --launch] [--feed DIR ...] \
  --door 'instagram_account=<open: what you pulled | closed: why>' \
  --door 'browser=<open: what you saved | closed: why>' [--pulled pulled] [--photos DIR] [--year YYYY]
```

Name every door you tried with `--door`, open or closed, in plain words ("closed: no Instagram tool in this
session"). gather.py adds the export and folder doors itself and records them all in `library.json`; `brief.md`
lists them. Each gather starts a new run folder; everything after it works in that one.

## When every door is closed

gather.py exits 3 and writes `out/brief.md` with one sentence on how to open a door. Tell the person exactly that
sentence and stop. Do not make a film from nothing.

## When there is no picture of the subject

The film opens on the subject, so it needs at least one picture of it. With no asset folder or link, no picture beside
`subject.md` and no post that mentions the subject, gather.py prints `not delivered: ` and one sentence naming what is
missing, and exits 2. Tell the person exactly that sentence and stop.

## Done when

`library.json` exists with its `subject` block (name, kind, facts, pictures, and a date when it is a launch), its
`settings` and its `feed`, and gather.py's summary names the subject, its kind, its stills and clips and the feed's
photographs. Read its `assumptions`; they go into `brief.md` as they are.
