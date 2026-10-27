// The household's own record, kept in this browser under one key: hearts, the watched shelf, the spinner's nights,
// and whose turn it is. The inputs file is the list; this is everything the household did with it.

const STORE_KEY = "movie-night:state";

export function slugOf(text) {
  return String(text)
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function filmKey(title, year) {
  return year ? `${slugOf(title)}-${year}` : slugOf(title);
}

export function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function readFilms(config) {
  return (Array.isArray(config.films) ? config.films : []).map((f) => ({
    key: f.key || filmKey(f.title, f.year),
    title: String(f.title),
    year: f.year ?? null,
    note: f.note || "",
    poster: f.poster || null,
    runtime: f.runtime ?? null,
    rating: f.rating ?? null,
    hearts: Array.isArray(f.hearts) ? f.hearts.slice() : [],
  }));
}

function blank() {
  return { hearts: {}, watched: [], history: [], stars: {}, turn: 0, seeded: [] };
}

function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    return s && typeof s === "object" ? { ...blank(), ...s } : null;
  } catch {
    return null;
  }
}

function clean(s, people) {
  const out = blank();
  if (s.hearts && typeof s.hearts === "object") {
    for (const [key, names] of Object.entries(s.hearts)) {
      if (Array.isArray(names)) out.hearts[key] = names.filter((n) => people.includes(n));
    }
  }
  if (Array.isArray(s.watched)) {
    out.watched = s.watched
      .filter((w) => w && typeof w.key === "string" && typeof w.title === "string" && typeof w.date === "string")
      .map((w) => ({ key: w.key, title: w.title, year: w.year ?? null, date: w.date, stars: clampStars(w.stars) }));
  }
  if (Array.isArray(s.history)) {
    out.history = s.history.filter((h) => h && typeof h.key === "string" && typeof h.date === "string").slice(-200);
  }
  out.turn = Number.isInteger(s.turn) ? s.turn : 0;
  out.seeded = Array.isArray(s.seeded) ? s.seeded.filter((k) => typeof k === "string") : [];
  return out;
}

function clampStars(n) {
  return Math.max(0, Math.min(5, Math.round(Number(n) || 0)));
}

export function createStore(config, films) {
  const people = Array.isArray(config.people) && config.people.length ? config.people.map(String) : ["You"];
  const stored = load();
  let s = stored ? clean(stored, people) : blank();
  const fresh = !stored;

  for (const w of Array.isArray(config.watched) ? config.watched : []) {
    const key = w.key || filmKey(w.title, w.year);
    if (s.seeded.includes(key)) continue;
    s.seeded.push(key);
    if (!s.watched.some((x) => x.key === key)) {
      s.watched.push({ key, title: String(w.title), year: w.year ?? null, date: String(w.date), stars: clampStars(w.stars) });
    }
  }

  const listeners = new Set();
  const save = () => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(s));
    } catch {
      // A browser that refuses storage keeps this visit's choices in memory.
    }
    for (const fn of listeners) fn();
  };
  save();

  const byKey = new Map(films.map((f) => [f.key, f]));

  return {
    fresh,
    people,
    onChange(fn) {
      listeners.add(fn);
    },
    hearts(film) {
      return s.hearts[film.key] ?? film.hearts.filter((n) => people.includes(n));
    },
    heartCount(film) {
      return this.hearts(film).length;
    },
    toggleHeart(film, name) {
      const now = this.hearts(film);
      s.hearts[film.key] = now.includes(name) ? now.filter((n) => n !== name) : [...now, name];
      save();
      return s.hearts[film.key].includes(name);
    },
    get turn() {
      return ((s.turn % people.length) + people.length) % people.length;
    },
    get person() {
      return people[this.turn];
    },
    get nextPerson() {
      return people[(this.turn + 1) % people.length];
    },
    passTurn() {
      s.turn = (this.turn + 1) % people.length;
      save();
    },
    isWatched(key) {
      return s.watched.some((w) => w.key === key);
    },
    onWall() {
      return films.filter((f) => !this.isWatched(f.key));
    },
    watched() {
      return s.watched.slice().sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    },
    markWatched(film) {
      if (this.isWatched(film.key)) return;
      s.watched.push({ key: film.key, title: film.title, year: film.year, date: today(), stars: 0 });
      save();
    },
    unwatch(key) {
      s.watched = s.watched.filter((w) => w.key !== key);
      save();
    },
    setStars(key, n) {
      const w = s.watched.find((x) => x.key === key);
      if (!w) return;
      w.stars = w.stars === n ? n - 1 : clampStars(n);
      save();
    },
    tonight() {
      const date = today();
      for (let i = s.history.length - 1; i >= 0; i -= 1) {
        const h = s.history[i];
        if (h.date === date && byKey.has(h.key) && !this.isWatched(h.key)) return byKey.get(h.key);
      }
      return null;
    },
    pick(film, by) {
      s.history.push({ date: today(), key: film.key, title: film.title, by });
      save();
    },
    nights() {
      return s.history.length;
    },
    exportJson() {
      return JSON.stringify({ app: "movie-night", exported: new Date().toISOString(), ...s }, null, 2);
    },
    importJson(text) {
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        return { ok: false, message: "That file is not JSON, so nothing changed." };
      }
      if (!data || data.app !== "movie-night") {
        return { ok: false, message: "That file is not a Movie Night export, so nothing changed." };
      }
      s = clean(data, people);
      save();
      const hearts = Object.values(s.hearts).reduce((n, list) => n + list.length, 0);
      return {
        ok: true,
        message: `Imported ${s.watched.length} watched ${s.watched.length === 1 ? "film" : "films"}, ${hearts} ${hearts === 1 ? "heart" : "hearts"}, and ${s.history.length} ${s.history.length === 1 ? "night" : "nights"}.`,
      };
    },
  };
}
