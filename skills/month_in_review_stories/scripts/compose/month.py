"""The month a series is made from, read from month.json: the month's posts with their days, types, captions,
photographs, places, likes and comments, the handle (the account's username, only when their data carries one), what the
person asked for (taste.json `ask`: their numbers, a length inside SECONDS, the series), and the three or four moments
the series tells: the ones the agent picked into taste.json (each named by its post's photograph, or by its day when
the post has none, with the line it says on screen, the shot it wrote for its photograph, and one of them the peak),
else the month's own story as its captions tell it (`story`): its first post and its last, and between them the posts
whose captions say the most, the one that says the most of all the peak. Likes and comments never choose a moment; their
figures reach the screen only when the ask is for their numbers. The look a board dresses the month in is
compose/look.py's."""
import calendar
import datetime as dt

from . import look

NAMES = [calendar.month_name[i].lower() for i in range(1, 13)]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
SHORT_WORDS = {"a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "or", "my", "by", "with", "is", "it", "no", "so"}
# how many moments the series tells, and the count it tells when nothing names one
MOMENTS = (3, 4)
# the lengths, in seconds, the reel is made at: an ask outside them is refused and nothing is made
SECONDS = (12, 30)
# the reel's length, in seconds, when the ask names none
LENGTH = 15


class OutOfRange(ValueError):
    """An asked length the reel cannot run."""

    def __init__(self, seconds):
        self.seconds = seconds
        super().__init__(f"not delivered: this kit makes a reel of {SECONDS[0]} to {SECONDS[1]} s, and the ask is for {float(seconds):g} s. "
                         f"Ask for a length in that range.")


def number(n):
    """A count in words up to twelve, else in figures."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def figure(n, one, many):
    return f"{n:,} {one if n == 1 else many}"


def name_of(caption):
    """What a post is called in a sentence: its caption's first sentence."""
    return caption.split(".")[0].strip().lower()


class Post:
    def __init__(self, d, year, month):
        self.day = int(d["day"])
        self.type = "reel" if d.get("type") in ("reel", "video", "clip") else "photo"
        self.caption = (d.get("caption") or "").strip()
        self.name = (d.get("name") or name_of(self.caption) or self.type).strip()
        self.place = (d.get("place") or "").strip().lower()
        self.photo = d.get("photo")
        # the shot the agent wrote for a moment's photograph (taste.json `moments[].shot`)
        self.shot = {}
        self.likes, self.comments = d.get("likes"), d.get("comments")
        # the words the post says on screen: the moment's line from taste.json, else its whole caption
        self.said = self.caption
        self.weekday = WEEKDAYS[dt.date(year, month, self.day).weekday()]

    def __repr__(self):
        return f"<{self.day} {self.type} {self.name!r}>"

    @property
    def counted(self):
        return self.likes is not None or self.comments is not None

    @property
    def weight(self):
        """How much of the month's story the post's caption tells: its words, and a place it names."""
        return len(self.caption.split()) + (3 if self.place else 0)

    def count(self):
        """The post's figures as the card says them, each only when the data carries it: 1,180 likes · 96 comments."""
        return "  ·  ".join(figure(n, one, many) for n, one, many in ((self.likes, "like", "likes"), (self.comments, "comment", "comments"))
                            if n is not None)


class Period:
    """One calendar month: its name, its short name and its length."""

    def __init__(self, year, month):
        self.year, self.month = year, month
        self.key = f"{year}-{month:02d}"
        self.name = NAMES[month - 1]
        self.short = self.name[:3]
        self.letter = self.name[0]
        self.days = calendar.monthrange(year, month)[1]

    def after(self, k=1):
        n = self.year * 12 + self.month - 1 + k
        return Period(n // 12, n % 12 + 1)


def which(posts, x):
    """The index of the post a moment names in `posts` (month.json rows): the post whose photograph it names, else the
    post of its day that has no photograph; None when no post is."""
    photo = x.get("photo")
    return next((i for i, p in enumerate(posts) if (p.get("photo") == photo if photo else
                                                    str(p.get("day")) == str(x.get("day")) and not p.get("photo"))), None)


def story(posts, n=MOMENTS[0]):
    """The n posts that tell the month as its captions tell it, in date order: the first and the last, and between them
    the ones whose captions say the most (the earlier between equals); all of them when there are no more than n."""
    if len(posts) <= n:
        return list(posts)
    ends = [posts[0], posts[-1]]
    middle = sorted(posts[1:-1], key=lambda x: (-x.weight, x.day))[:n - 2]
    return sorted(ends + middle, key=lambda x: x.day)


class Month:
    """The month as the reel and the cards tell it: its posts, and the moments of it the series shows in date order."""

    def __init__(self, d):
        m = d["month"]
        self.period = Period(int(m["year"]), int(m["month"]))
        p = self.period
        self.year, self.name, self.short, self.letter, self.days = p.year, p.name, p.short, p.letter, p.days
        self.label = f"{p.name} {p.year}"
        self.next = p.after(1)
        # the handle is the account's username as their data carries it; with none, no card carries a handle line
        h = (d.get("handle") or "").strip().lstrip("@")
        self.handle = f"@{h}" if h else None
        rows = list(d["posts"])
        made = [Post(x, p.year, p.month) for x in rows]
        self.posts = sorted(made, key=lambda x: x.day)
        if len(self.posts) < MOMENTS[0]:
            raise ValueError(f"{len(self.posts)} posts in {self.label}; the series needs at least {MOMENTS[0]}")
        ask = d.get("ask") or {}
        # their numbers reach the screen only when they asked for them and the data carries them
        self.counted = bool(ask.get("counts")) and any(x.counted for x in self.posts)
        self.seconds = ask.get("seconds") or None
        if self.seconds is not None and not SECONDS[0] <= float(self.seconds) <= SECONDS[1]:
            raise OutOfRange(self.seconds)
        self.series = bool(ask.get("series"))
        picked = d.get("moments") or []
        if picked:
            at = [which(rows, x) for x in picked]
            gone = [x.get("photo") or f"day {x.get('day')} with no photograph" for x, i in zip(picked, at) if i is None]
            if gone:
                raise ValueError(f"taste.json moments name no post in {self.label}: {gone}")
            if not MOMENTS[0] <= len(set(at)) <= MOMENTS[-1]:
                raise ValueError(f"taste.json names {len(picked)} moments; the series tells {MOMENTS[0]} or {MOMENTS[-1]}")
            for x, i in zip(picked, at):
                post = made[i]
                post.said = (x.get("line") or "").strip()
                post.name = (x.get("what") or post.name).strip()
                post.shot = x.get("shot") or {}
            self.moments = sorted({made[i] for i in at}, key=lambda x: x.day)
            self.peak = next((made[i] for x, i in zip(picked, at) if x.get("peak")), None)
        else:
            # a given look's card count, when the series can tell that many
            n = (d.get("look") or {}).get("cards")
            n = n if n in MOMENTS else MOMENTS[0]
            self.moments = story(self.posts, n)
            self.peak = max(self.moments, key=lambda x: (x.weight, -x.day)) if len(self.moments) > 1 else None
        # the look the person gave and the swatches taste.json gives, which every board's style dresses the month with
        self.look, self.given_swatches = d.get("look"), d.get("swatches")
        look.measure(self)

    @property
    def lead(self):
        """The moment the reel opens on: the peak, else the first."""
        return self.peak or self.moments[0]

    @property
    def walk(self):
        """The moments in the order the reel shows each of them once: the lead, then the others in date order."""
        return [self.lead] + [x for x in self.moments if x is not self.lead]


def fill(text, width, limit):
    """Lines of text no wider than limit, filled greedily at words, and a word wider than limit broken at the last
    letter that fits."""
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if cur and width(t) > limit:
            lines.append(cur)
            cur = w
        else:
            cur = t
        while len(cur) > 1 and width(cur) > limit:
            k = max((i for i in range(1, len(cur)) if width(cur[:i]) <= limit), default=1)
            lines.append(cur[:k])
            cur = cur[k:]
    if cur:
        lines.append(cur)
    return lines


def wrap(text, width, limit, sentence=True):
    """Lines of text no wider than limit, breaking first at a sentence end, then at words with each sentence's lines as
    even as they go: the narrowest measure that still sets it on as many lines as limit does, so its last line never
    holds one word alone."""
    parts = [text]
    if sentence:
        words, parts, cur = text.split(), [], []
        for w in words:
            cur.append(w)
            if w.endswith((".", ";")):
                parts.append(" ".join(cur))
                cur = []
        if cur:
            parts.append(" ".join(cur))
    lines = []
    for part in parts:
        n, lo, hi = len(fill(part, width, limit)), 0, limit
        while n > 1 and hi - lo > 1:
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if len(fill(part, width, mid)) <= n else (mid, hi)
        lines += fill(part, width, hi)
    return lines


def fit(text, width, limit):
    """The words as they fit on one line: whole, else the first line they wrap to, cut back to leave room for an ellipsis."""
    lines = fill(text, width, limit)
    if len(lines) <= 1:
        return text
    head = lines[0]
    while len(head) > 1 and width(head + "…") > limit:
        head = head.rsplit(" ", 1)[0] if " " in head else head[:-1]
    return head + "…"
