// The watering log and the notes, kept in this browser's localStorage and nowhere else.
// The log is { <plantId>: [ISO date-times, oldest first] } under "plant-keeper:v1".
const LOG_KEY = "plant-keeper:v1";
const NOTES_KEY = "plant-keeper:notes";

function read(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? "null");
    return value !== null && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

const isWhen = (v) => typeof v === "string" && !Number.isNaN(Date.parse(v));

/** A log with only well-formed entries, each list sorted and without repeats. */
export function cleanLog(raw) {
  const log = {};
  for (const [id, list] of Object.entries(raw ?? {})) {
    if (!Array.isArray(list)) continue;
    const times = [...new Set(list.filter(isWhen).map((v) => new Date(v).toISOString()))].sort();
    if (times.length) log[id] = times;
  }
  return log;
}

export const loadLog = () => cleanLog(read(LOG_KEY));
export const saveLog = (log) => write(LOG_KEY, log);
export const loadNotes = () => Object.fromEntries(Object.entries(read(NOTES_KEY)).filter(([, v]) => typeof v === "string"));
export const saveNotes = (notes) => write(NOTES_KEY, notes);

export function clearAll() {
  try {
    localStorage.removeItem(LOG_KEY);
    localStorage.removeItem(NOTES_KEY);
  } catch {
    // Nothing stored to clear.
  }
}

export function lastWatering(log, id) {
  const list = log[id];
  return list?.length ? Date.parse(list[list.length - 1]) : null;
}

/** Records a watering at `t`; a second one on the same calendar day takes the place of the first. */
export function addWatering(log, id, t, sameDay) {
  const list = (log[id] ?? []).filter((v) => !sameDay(Date.parse(v), t));
  list.push(new Date(t).toISOString());
  log[id] = [...new Set(list)].sort();
}

export function removeWatering(log, id, iso) {
  log[id] = (log[id] ?? []).filter((v) => v !== iso);
}

/** What Export downloads. */
export function exportFile(log, notes, now) {
  return JSON.stringify({ app: "plant-keeper", exported: new Date(now).toISOString(), log, notes }, null, 2);
}

/** Reads an exported file (or a bare log) and merges it into `log` and `notes`. Answers what it added. */
export function mergeImport(text, log, notes) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("That file is not a Plant Keeper export.");
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) throw new Error("That file is not a Plant Keeper export.");
  const incoming = cleanLog(data.log && typeof data.log === "object" ? data.log : data);
  const ids = Object.keys(incoming);
  if (!ids.length) throw new Error("That file has no waterings in it.");
  let added = 0;
  for (const id of ids) {
    const before = new Set(log[id] ?? []);
    for (const t of incoming[id]) if (!before.has(t)) added += 1;
    log[id] = [...new Set([...(log[id] ?? []), ...incoming[id]])].sort();
  }
  if (data.notes && typeof data.notes === "object") {
    for (const [id, v] of Object.entries(data.notes)) if (typeof v === "string" && v.trim() && !notes[id]) notes[id] = v;
  }
  return { added, plants: ids.length };
}
