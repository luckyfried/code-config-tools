# Link in Bio

## What this makes

A single page for the link in your bio. Your picture and name sit on a card that tilts toward the pointer (or with the phone itself), over a color field that drifts slowly. Under them are your links, your social profiles, a QR code that opens the page, and a Save contact button that adds you to a phone's contacts. On a phone, press and hold any link to copy it, and Share opens the phone's share sheet with the page's address (on a computer it copies the address). The page works on phones and desktops, follows the visitor's light or dark setting, and is a folder of plain files that any static host serves.

## Run

Put `link-in-bio.inputs.json` and the avatar picture in the project folder, then:

```
cd <project> && python3 <agent-apps root>/link-in-bio/scripts/run.py
```

It writes `out/link-in-bio/`. Running it again replaces that folder with the same files. If a key is missing or wrong, it prints one plain line for each problem and writes nothing.

## Check

- `out/link-in-bio/index.html` has the person's name inside `<h1>`.
- Every link in the inputs is an `<a>` in `index.html` with its address.
- The avatar is in `out/link-in-bio/media/`.
- `out/link-in-bio/contact.vcf` exists and carries the person's name.
- `out/link-in-bio/config.js` carries the page's `url`, and the QR code on the page opens exactly that address.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/link-in-bio
```

Then open http://localhost:8000/. To put it online, upload the `out/link-in-bio/` folder to any static host, and use the address it gets as `url`.

## Make it yours

Ask the person for all of this in one message:

- `name`: their name as it should appear.
- `line`: a one-line intro, such as what they make and where.
- `avatar`: a picture of them (.jpg, .png, .webp, .gif, .svg, or .avif). Copy it into the project folder and put its file name here.
- `url`: the web address the page will live at. The QR code opens this address.
- `links`: the links to show, top to bottom. Each has a `label`, a `url` (https://, http://, mailto:, or tel:), and an optional `icon`: link, shop, calendar, mail, letter, play, music, mic, camera, book, heart, star, pin, chat, code, gift, or globe.
- `socials` (optional): handles or full addresses for instagram, tiktok, youtube, x, threads, bluesky, mastodon (as user@server), github, linkedin, pinterest, twitch, dribbble, facebook, spotify (full address), and website (full address).
- `vcard` (optional): a `phone` and an `email` for the Save contact card.
- `theme` (optional): dawn (warm peach and rose), dusk (deep violet and teal), mono (ink and paper), or candy (bright pink, lime, and sky). The default is dawn.

`inputs.example.json` in this folder shows every key filled in.
