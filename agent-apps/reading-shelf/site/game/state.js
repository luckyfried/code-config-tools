// The library: books from config.js, the person's edits from this device, the sort, and change events.
const EDITS_KEY = "reading-shelf:edits";
const SORT_KEY = "reading-shelf:sort";
const STATUSES = ["read", "reading", "want"];

export const SORTS = [
  { id: "shelf", label: "Shelf order" },
  { id: "title", label: "Title" },
  { id: "author", label: "Author" },
  { id: "recent", label: "Recently read" },
  { id: "rating", label: "Rating" },
  { id: "pages", label: "Length" },
  { id: "status", label: "Reading status" },
];

export function slug(text) {
  return String(text || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function readJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full or blocked: the edit still holds for this visit.
  }
}

function normalize(raw, index) {
  const title = String(raw.title || "Untitled").trim();
  const author = String(raw.author || "").trim();
  const status = STATUSES.includes(raw.status) ? raw.status : "want";
  const pages = Math.max(0, Math.round(Number(raw.pages) || 0));
  const rating = Math.max(0, Math.min(5, Math.round(Number(raw.rating) || 0)));
  const page = Math.max(0, Math.min(pages || Infinity, Math.round(Number(raw.page) || 0)));
  return {
    id: slug(`${title}-${author}`) || `book-${index}`,
    order: index,
    title,
    author,
    isbn: raw.isbn ? String(raw.isbn).replace(/[^0-9Xx]/g, "") : "",
    status,
    rating,
    note: raw.note ? String(raw.note).trim() : "",
    started: raw.started || "",
    finished: raw.finished || "",
    pages,
    page,
    cover: raw.cover || "",
  };
}

const sortTitle = (t) => t.replace(/^(the|a|an)\s+/i, "");
const surname = (a) => {
  const parts = a.split(/\s+/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : "";
};
const STATUS_RANK = { reading: 0, read: 1, want: 2 };

export function sortBooks(books, by) {
  const list = books.slice();
  const byTitle = (a, b) => sortTitle(a.title).localeCompare(sortTitle(b.title));
  switch (by) {
    case "title":
      return list.sort(byTitle);
    case "author":
      return list.sort((a, b) => surname(a.author).localeCompare(surname(b.author)) || byTitle(a, b));
    case "pages":
      return list.sort((a, b) => b.pages - a.pages || byTitle(a, b));
    case "rating":
      return list.sort((a, b) => b.rating - a.rating || byTitle(a, b));
    case "recent":
      return list.sort((a, b) => {
        const ra = a.status === "reading" ? "9999" : a.finished || "";
        const rb = b.status === "reading" ? "9999" : b.finished || "";
        return rb.localeCompare(ra) || byTitle(a, b);
      });
    case "status":
      return list.sort((a, b) => STATUS_RANK[a.status] - STATUS_RANK[b.status] || a.order - b.order);
    default:
      return list.sort((a, b) => a.order - b.order);
  }
}

export function createStore(config) {
  const base = (Array.isArray(config.books) ? config.books : []).map(normalize);
  const seen = new Set();
  for (const book of base) {
    while (seen.has(book.id)) book.id += "-2";
    seen.add(book.id);
  }
  let edits = readJSON(EDITS_KEY, {});
  const listeners = new Set();
  const books = base.map((b) => ({ ...b, ...pick(edits[b.id]) }));
  let sort = SORTS.some((s) => s.id === readJSON(SORT_KEY, "")) ? readJSON(SORT_KEY, "") : "shelf";

  function pick(edit) {
    if (!edit || typeof edit !== "object") return {};
    const out = {};
    if (STATUSES.includes(edit.status)) out.status = edit.status;
    if (Number.isFinite(edit.rating)) out.rating = Math.max(0, Math.min(5, Math.round(edit.rating)));
    if (Number.isFinite(edit.page)) out.page = Math.max(0, Math.round(edit.page));
    if (typeof edit.started === "string") out.started = edit.started;
    if (typeof edit.finished === "string") out.finished = edit.finished;
    return out;
  }

  const emit = (type, detail) => listeners.forEach((fn) => fn(type, detail));

  return {
    owner: String(config.owner || "").trim(),
    books,
    get sort() {
      return sort;
    },
    byId: (id) => books.find((b) => b.id === id),
    sorted: () => sortBooks(books, sort),
    on(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    setSort(next) {
      if (next === sort || !SORTS.some((s) => s.id === next)) return;
      sort = next;
      writeJSON(SORT_KEY, sort);
      emit("sort", { sort });
    },
    update(id, patch) {
      const book = books.find((b) => b.id === id);
      if (!book) return;
      const clean = pick(patch);
      const today = new Date().toISOString().slice(0, 10);
      if (clean.status === "reading" && book.status !== "reading" && !book.started) clean.started = today;
      if (clean.status === "read" && book.status !== "read" && !book.finished) clean.finished = today;
      if (clean.page !== undefined && book.pages) clean.page = Math.min(clean.page, book.pages);
      const before = book.status;
      Object.assign(book, clean);
      edits = { ...edits, [id]: { ...(edits[id] || {}), ...clean } };
      writeJSON(EDITS_KEY, edits);
      emit("change", { id, patch: clean, statusChanged: before !== book.status });
    },
    exportJSON() {
      const out = {
        owner: config.owner || "",
        books: books.map((b) => ({
          title: b.title,
          author: b.author,
          isbn: b.isbn,
          status: b.status,
          rating: b.rating,
          note: b.note,
          started: b.started,
          finished: b.finished,
          pages: b.pages,
          page: b.page,
        })),
      };
      return JSON.stringify(out, null, 2);
    },
    importJSON(text) {
      const data = JSON.parse(text);
      const list = Array.isArray(data) ? data : data.books;
      if (!Array.isArray(list)) throw new Error("That file has no books in it.");
      let matched = 0;
      for (const raw of list) {
        const id = slug(`${raw.title || ""}-${raw.author || ""}`);
        const book = books.find((b) => b.id === id);
        if (!book) continue;
        const clean = pick(raw);
        Object.assign(book, clean);
        edits = { ...edits, [id]: { ...(edits[id] || {}), ...clean } };
        matched += 1;
      }
      writeJSON(EDITS_KEY, edits);
      emit("change", { id: null, patch: {}, statusChanged: true });
      return matched;
    },
  };
}
