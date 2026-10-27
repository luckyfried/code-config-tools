// Everything the person does lives in localStorage under one key, so a reload changes nothing.
const KEY = "focus-blocks";

export function load() {
  let raw = null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    return null;
  }
  if (!raw) return null;
  try {
    return clean(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function save(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* A full or blocked storage keeps the page running; the blocks stay in memory for this visit. */
  }
}

export function isBlock(b) {
  return (
    b && typeof b === "object" && Number.isFinite(b.start) && Number.isFinite(b.end) && b.end > b.start &&
    (b.label === undefined || typeof b.label === "string")
  );
}

function clean(s) {
  const out = { blocks: [], active: null, pick: null };
  if (!s || typeof s !== "object") return out;
  if (Array.isArray(s.blocks)) out.blocks = s.blocks.filter(isBlock).map((b) => ({ start: b.start, end: b.end, label: b.label || "" }));
  const a = s.active;
  if (a && Number.isFinite(a.start) && Number.isFinite(a.ms) && a.ms > 0) {
    out.active = {
      start: a.start,
      ms: a.ms,
      label: typeof a.label === "string" ? a.label : "",
      pausedAt: Number.isFinite(a.pausedAt) ? a.pausedAt : null,
      pausedMs: Number.isFinite(a.pausedMs) ? a.pausedMs : 0,
    };
    if (a.next && Number.isFinite(a.next.minutes) && a.next.minutes > 0) {
      out.active.next = { minutes: a.next.minutes, label: String(a.next.label || "") };
    }
  }
  if (s.pick && Number.isFinite(s.pick.minutes)) out.pick = { minutes: s.pick.minutes, label: String(s.pick.label || "") };
  out.blocks.sort((x, y) => x.start - y.start);
  return out;
}

// Adds blocks from an exported file; a block with the same start as one already kept is the same block.
export function merge(blocks, incoming) {
  const seen = new Set(blocks.map((b) => b.start));
  let added = 0;
  for (const b of incoming) {
    if (!isBlock(b) || seen.has(b.start)) continue;
    blocks.push({ start: b.start, end: b.end, label: b.label || "" });
    seen.add(b.start);
    added += 1;
  }
  blocks.sort((x, y) => x.start - y.start);
  return added;
}
