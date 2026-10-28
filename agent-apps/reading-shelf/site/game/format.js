// Words and numbers as the page says them.
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export const num = (n) => Math.round(n).toLocaleString("en-US");

export function possessive(name) {
  if (!name) return "Your shelf";
  return `${name}’s shelf`;
}

export function parseDate(text) {
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(text || "");
  if (!m) return null;
  return { y: Number(m[1]), m: Number(m[2]) - 1, d: m[3] ? Number(m[3]) : null };
}

export function longDate(text) {
  const p = parseDate(text);
  if (!p) return "";
  return p.d ? `${MONTHS[p.m]} ${p.d}, ${p.y}` : `${MONTHS[p.m]} ${p.y}`;
}

export const monthShort = (m) => MONTHS[m].slice(0, 3);
export const monthName = (m) => MONTHS[m];

export function statusWords(book) {
  if (book.status === "reading") {
    if (book.pages) return `Reading, page ${num(book.page)} of ${num(book.pages)}`;
    return "Reading now";
  }
  if (book.status === "read") return book.finished ? `Finished ${longDate(book.finished)}` : "Read";
  return "Want to read";
}

export function joinAnd(items) {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}
