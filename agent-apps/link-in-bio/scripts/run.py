"""Writes the Link in Bio page from link-in-bio.inputs.json in the current folder.

Run from the project folder:  python3 <agent-apps root>/link-in-bio/scripts/run.py
Reads link-in-bio.inputs.json and the avatar file beside it; writes out/link-in-bio/.
"""

import base64
import html
import json
import shutil
import sys
from pathlib import Path

SLUG = "link-in-bio"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"

KEYS = {"name", "line", "avatar", "url", "links", "socials", "vcard", "theme", "_notes"}
REQUIRED = ["name", "line", "avatar", "url", "links"]
LINK_KEYS = {"label", "url", "icon"}
VCARD_KEYS = {"phone", "email"}
LINK_ICONS = [
    "link", "shop", "calendar", "mail", "letter", "play", "music", "mic", "camera", "book",
    "heart", "star", "pin", "chat", "code", "gift", "globe",
]
SCHEMES = ("https://", "http://", "mailto:", "tel:")
IMAGE_TYPES = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": None, ".gif": "GIF", ".svg": None, ".avif": None}

# Each network: its name on the page and the address a bare handle becomes.
NETWORKS = {
    "instagram": ("Instagram", "https://instagram.com/{}"),
    "tiktok": ("TikTok", "https://www.tiktok.com/@{}"),
    "youtube": ("YouTube", "https://youtube.com/@{}"),
    "x": ("X", "https://x.com/{}"),
    "threads": ("Threads", "https://www.threads.net/@{}"),
    "bluesky": ("Bluesky", "https://bsky.app/profile/{}"),
    "mastodon": ("Mastodon", None),
    "github": ("GitHub", "https://github.com/{}"),
    "linkedin": ("LinkedIn", "https://www.linkedin.com/in/{}"),
    "pinterest": ("Pinterest", "https://pinterest.com/{}"),
    "twitch": ("Twitch", "https://twitch.tv/{}"),
    "dribbble": ("Dribbble", "https://dribbble.com/{}"),
    "facebook": ("Facebook", "https://facebook.com/{}"),
    "spotify": ("Spotify", None),
    "website": ("Website", None),
}
NETWORK_ICONS = {"website": "globe"}


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def social_url(network, value):
    value = value.strip()
    if value.startswith(("https://", "http://")):
        return value
    handle = value.lstrip("@")
    if network == "mastodon":
        if "@" not in handle:
            return None
        user, server = handle.split("@", 1)
        return f"https://{server}/@{user}"
    template = NETWORKS[network][1]
    return template.format(handle) if template else None


def validate(data):
    problems = []
    name = f"{SLUG}.inputs.json"
    if not isinstance(data, dict):
        fail([f"{name} must hold one object with the keys name, line, avatar, url, and links."])
    for key in data:
        if key not in KEYS:
            problems.append(f'{name} has the key "{key}", which this app does not use.')
    for key in REQUIRED:
        if key not in data:
            problems.append(f'{name} is missing the key "{key}".')
    for key in ("name", "line", "avatar", "url"):
        if key in data and not is_text(data[key]):
            problems.append(f'In {name}, "{key}" must be some text.')
    if is_text(data.get("url")) and not data["url"].startswith(("https://", "http://")):
        problems.append(f'In {name}, "url" must be the page\'s own web address, starting with https://.')

    links = data.get("links")
    if "links" in data:
        if not isinstance(links, list) or not links:
            problems.append(f'In {name}, "links" must be a list with at least one link.')
        else:
            for n, link in enumerate(links, 1):
                if not isinstance(link, dict):
                    problems.append(f"In {name}, link {n} must be an object with a label and a url.")
                    continue
                for key in link:
                    if key not in LINK_KEYS:
                        problems.append(f'In {name}, link {n} has the key "{key}"; a link takes label, url, and icon.')
                if not is_text(link.get("label")):
                    problems.append(f'In {name}, link {n} is missing its "label".')
                if not is_text(link.get("url")):
                    problems.append(f'In {name}, link {n} is missing its "url".')
                elif not link["url"].strip().startswith(SCHEMES):
                    problems.append(
                        f'In {name}, link {n} has the address "{link["url"]}"; '
                        "an address starts with https://, http://, mailto:, or tel:."
                    )
                icon = link.get("icon", "link")
                if icon not in LINK_ICONS:
                    problems.append(f'In {name}, link {n} has the icon "{icon}"; the icons are {", ".join(LINK_ICONS)}.')

    socials = data.get("socials", {})
    if not isinstance(socials, dict):
        problems.append(f'In {name}, "socials" must be an object such as {{"instagram": "yourname"}}.')
    else:
        for network, value in socials.items():
            if network not in NETWORKS:
                problems.append(f'In {name}, "socials" has "{network}"; the networks are {", ".join(NETWORKS)}.')
            elif not is_text(value):
                problems.append(f'In {name}, "socials.{network}" must be a handle or an address.')
            elif social_url(network, value) is None:
                problems.append(f'In {name}, "socials.{network}" must be a full address starting with https://.')

    vcard = data.get("vcard", {})
    if not isinstance(vcard, dict):
        problems.append(f'In {name}, "vcard" must be an object with "phone" and "email".')
    else:
        for key, value in vcard.items():
            if key not in VCARD_KEYS:
                problems.append(f'In {name}, "vcard" has the key "{key}"; it takes phone and email.')
            elif not is_text(value):
                problems.append(f'In {name}, "vcard.{key}" must be some text.')

    theme = data.get("theme", "dawn")
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    if theme not in themes:
        problems.append(f'In {name}, "theme" is "{theme}"; the themes are {", ".join(themes)}.')

    avatar = data.get("avatar")
    if is_text(avatar):
        path = Path(avatar)
        if path.suffix.lower() not in IMAGE_TYPES:
            problems.append(f'The avatar "{avatar}" must be a picture: .jpg, .png, .webp, .gif, .svg, or .avif.')
        elif not path.is_file():
            problems.append(f'The avatar file "{avatar}" is not in this folder.')
    if problems:
        fail(problems)


def esc(value):
    return html.escape(value.strip(), quote=True)


def icon(name):
    return f'<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-{name}"></use></svg>'


def display_address(url):
    shown = url.split("://", 1)[-1]
    return shown[:-1] if shown.endswith("/") else shown


def link_address(url):
    for scheme in ("mailto:", "tel:"):
        if url.startswith(scheme):
            return url[len(scheme):].split("?", 1)[0]
    shown = display_address(url).split("?", 1)[0]
    return shown[4:] if shown.startswith("www.") else shown


def render_profile(data, avatar_href):
    name = data["name"].strip()
    socials = data.get("socials", {})
    out = [
        '<div class="lift">',
        '<article class="card" aria-labelledby="profile-name">',
        '<div class="card__sheen" aria-hidden="true"></div>',
        '<div class="card__rim" aria-hidden="true"></div>',
        '<header class="identity">',
        '<div class="avatar enter"><div class="avatar__halo" aria-hidden="true">'
        '<span class="avatar__glow"></span><span class="avatar__ring"></span></div>'
        f'<img class="avatar__img" src="{esc(avatar_href)}" alt="{esc(name)}" width="132" height="132" '
        'decoding="async" fetchpriority="high"></div>',
        f'<h1 class="name" id="profile-name">{esc(name)}</h1>',
        f'<p class="line enter">{esc(data["line"])}</p>',
    ]
    if socials:
        out.append('<ul class="socials enter" aria-label="Elsewhere">')
        for network, value in socials.items():
            label = NETWORKS[network][0]
            href = social_url(network, value)
            out.append(
                f'<li><a class="social" href="{esc(href)}" aria-label="{esc(label)}">'
                f"{icon(NETWORK_ICONS.get(network, network))}</a></li>"
            )
        out.append("</ul>")
    out.append("</header>")

    out.append('<nav class="links" aria-label="Links"><ul>')
    for link in data["links"]:
        label = link["label"].strip()
        href = link["url"].strip()
        out.append(
            '<li class="enter"><div class="link">'
            f'<a class="link__main" href="{esc(href)}">'
            f'<span class="link__icon">{icon(link.get("icon", "link"))}</span>'
            f'<span class="link__text"><span class="link__label">{esc(label)}</span>'
            f'<span class="link__host">{esc(link_address(href))}</span></span></a></div></li>'
        )
    out.append("</ul></nav>")

    url = data["url"].strip()
    shown = display_address(url)
    file_name = "".join(ch for ch in name if ch not in '\\/:*?"<>|').strip() or "contact"
    out += [
        '<section class="share enter" aria-label="Share this page">',
        f'<div class="qr"><canvas class="qr__canvas" role="img" aria-label="QR code that opens {esc(shown)}"></canvas></div>',
        '<div class="share__body">',
        f'<p class="share__url">{esc(shown)}</p>',
        '<p class="share__hint">Scan to open this page.</p>',
        "</div>",
        '<div class="share__actions">',
        f'<a class="button button--primary" href="./contact.vcf" download="{esc(file_name)}.vcf">{icon("contact")}Save contact</a>',
        f'<button class="button button--quiet" type="button" data-share="{esc(url)}">{icon("share")}Share</button>',
        "</div></section>",
        "</article>",
        "</div>",
    ]
    return "\n    ".join(out)


def vcard_text(value):
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def render_vcard(data, avatar_path):
    name = data["name"].strip()
    words = name.split()
    family = words[-1] if len(words) > 1 else ""
    given = " ".join(words[:-1]) if len(words) > 1 else name
    card = data.get("vcard", {})
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{vcard_text(family)};{vcard_text(given)};;;",
        f"FN:{vcard_text(name)}",
        f"NOTE:{vcard_text(data['line'].strip())}",
        f"URL:{data['url'].strip()}",
    ]
    if is_text(card.get("phone")):
        lines.append(f"TEL;TYPE=CELL:{vcard_text(card['phone'].strip())}")
    if is_text(card.get("email")):
        lines.append(f"EMAIL;TYPE=INTERNET:{vcard_text(card['email'].strip())}")
    kind = IMAGE_TYPES.get(avatar_path.suffix.lower())
    if kind:
        photo = base64.b64encode(avatar_path.read_bytes()).decode("ascii")
        lines.append(f"PHOTO;ENCODING=b;TYPE={kind}:{photo}")
    lines.append("END:VCARD")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def fill(template, marker, value):
    if template.count(marker) != 1:
        fail([f"The page template in {SITE} is missing its {marker!r} slot; reinstall the app folder."])
    return template.replace(marker, value)


def main():
    inputs = Path.cwd() / f"{SLUG}.inputs.json"
    if not inputs.is_file():
        fail([f"Make {SLUG}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(inputs.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{SLUG}.inputs.json is not valid JSON: {err.msg} on line {err.lineno}."])
    validate(data)

    out = Path.cwd() / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    (out / "config.js").unlink(missing_ok=True)
    shutil.rmtree(out / "themes")

    avatar_path = Path(data["avatar"])
    media = out / "media"
    media.mkdir()
    shutil.copyfile(avatar_path, media / avatar_path.name)
    avatar_href = f"media/{avatar_path.name}"

    theme = data.get("theme", "dawn")
    shutil.copyfile(THEMES / f"{theme}.css", out / "theme.css")

    config = {key: value for key, value in data.items() if key != "_notes"}
    config["avatar"] = avatar_href
    config["theme"] = theme
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    page = (SITE / "index.html").read_text(encoding="utf-8")
    page = fill(page, "<title>Link in Bio</title>", f"<title>{esc(data['name'])}</title>")
    page = fill(page, '<meta name="description" content="">', f'<meta name="description" content="{esc(data["line"])}">')
    page = fill(page, "<!-- profile -->", render_profile(data, avatar_href))
    (out / "index.html").write_text(page, encoding="utf-8")

    (out / "contact.vcf").write_bytes(render_vcard(data, avatar_path).encode("utf-8"))

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
