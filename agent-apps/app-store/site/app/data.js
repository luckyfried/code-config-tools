// The store as Muse last read it, the person's Gets in the app's inbox, and what each app's button says.
//
// Live, the page reads the record store/current (written by `run.py --refresh` and `--work`, from `csc app store`)
// and the inbox from the app's own server. Opened without that server, it shows the sample in config.js and Get
// is off, since a Get needs the inbox.

const CONFIG = window.__APP_CONFIG__ || {};

export const CATEGORY_LABELS = {
  productivity: "Productivity",
  finance: "Finance",
  "health-fitness": "Health & fitness",
  lifestyle: "Lifestyle",
  social: "Social",
  education: "Education",
  business: "Business",
  "developer-tools": "Developer tools",
  utilities: "Utilities",
  entertainment: "Entertainment",
  "photo-video": "Photo & video",
  music: "Music",
  news: "News",
  reference: "Reference",
  shopping: "Shopping",
  travel: "Travel",
  "food-drink": "Food & drink",
  sports: "Sports",
  games: "Games",
  weather: "Weather",
};

export const state = {
  live: false,
  read: false,
  store: { apps: [], waiting: [], installed: [], readAt: null, problem: null },
  events: [],
};

function normalize(store) {
  const value = store && typeof store === "object" ? store : {};
  return {
    apps: Array.isArray(value.apps) ? value.apps : [],
    waiting: Array.isArray(value.waiting) ? value.waiting : [],
    installed: Array.isArray(value.installed) ? value.installed : [],
    readAt: typeof value.readAt === "string" ? value.readAt : null,
    problem: typeof value.problem === "string" ? value.problem : null,
  };
}

function sampleEvents() {
  const box = Array.isArray(CONFIG.sampleInbox) ? CONFIG.sampleInbox : [];
  return box.map((event, n) => ({
    id: `sample-${n + 1}`,
    action: event.action,
    status: event.status,
    at: event.at,
    payload: event.payload || {},
    key: `sample-${n + 1}`,
    error: event.error || null,
    result: event.result || null,
  }));
}

async function json(path, options) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `The app answered ${response.status}.`);
  return body;
}

/** Finds out once whether the app's own server answers; without it the page shows the sample. */
export async function connect() {
  try {
    const response = await fetch("api/health", { cache: "no-store" });
    const type = response.headers.get("content-type") || "";
    state.live = response.ok && type.includes("application/json");
  } catch {
    state.live = false;
  }
  await load();
}

/** Reads the store record and the inbox again; the sample when the server is not there. */
export async function load() {
  if (!state.live) {
    state.store = normalize(CONFIG.sample);
    state.events = sampleEvents();
    state.read = true;
    return;
  }
  const [records, inbox] = await Promise.all([json("api/records/store"), json("api/inbox")]);
  const current = Array.isArray(records) ? records.find((record) => record.id === "current") : null;
  state.read = Boolean(current);
  state.store = normalize(current ? current.body : null);
  state.events = Array.isArray(inbox) ? inbox : [];
}

function getsFor(appId) {
  return state.events.filter((event) => event.action === "get" && event.payload && event.payload.appId === appId);
}

/**
 * What one app's button shows:
 *   installed  Muse runs it; `address` is its link
 *   waiting    the person tapped Get and Muse has not started; `event` can be cancelled
 *   installing Muse has it, or the person got it in the store on the web
 *   failed     Muse could not install it; `reason` says why
 *   get        none of these
 */
export function stateOf(app) {
  const installed = state.store.installed.find((entry) => entry.appId === app.id);
  if (installed) return { kind: "installed", address: installed.address };
  const gets = getsFor(app.id).filter((event) => event.status !== "cancelled");
  const last = gets[gets.length - 1];
  if (last && last.status === "pending") return { kind: "waiting", event: last };
  if (last && last.status === "working") return { kind: "installing", event: last };
  if (last && last.status === "failed") return { kind: "failed", event: last, reason: last.error || "" };
  if (last && last.status === "completed" && last.result && last.result.address) {
    return { kind: "installed", address: last.result.address };
  }
  if (state.store.waiting.some((entry) => entry.appId === app.id)) return { kind: "installing" };
  return { kind: "get" };
}

/** Adds a Get to the inbox. The key is the app's shared toolkit, so a second tap is the same Get. */
export async function get(app) {
  const failed = getsFor(app.id).filter((event) => event.status === "failed").length;
  const key = failed === 0 ? app.sharedToolkitId : `${app.sharedToolkitId}-${failed + 1}`;
  const event = await json("api/inbox", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      action: "get",
      target: null,
      key,
      payload: { appId: app.id, title: app.title, sharedToolkitId: app.sharedToolkitId },
    }),
  });
  if (!state.events.some((known) => known.id === event.id)) state.events.push(event);
  return event;
}

/** Takes back a Get Muse has not started. */
export async function cancel(event) {
  const updated = await json(`api/inbox/${encodeURIComponent(event.id)}/cancel`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  state.events = state.events.map((known) => (known.id === updated.id ? updated : known));
  return updated;
}

/** The apps waiting for Muse, in the order they were got. */
export function waitingApps() {
  return state.store.apps.filter((app) => {
    const kind = stateOf(app).kind;
    return kind === "waiting" || kind === "installing";
  });
}

/** "12 minutes ago" for a time the store was read. */
export function ago(iso) {
  const at = Date.parse(iso || "");
  if (Number.isNaN(at)) return "";
  const minutes = Math.max(0, Math.round((Date.now() - at) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/** 1.2K for a count over a thousand. */
export function count(value) {
  const n = Number(value) || 0;
  if (n < 1000) return String(n);
  if (n < 10000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}K`;
  return `${Math.round(n / 1000)}K`;
}
