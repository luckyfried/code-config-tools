// Discover, Yours, and one app's page, drawn from the store and the inbox.
import { CATEGORY_LABELS, ago, cancel, count, get, state, stateOf, waitingApps } from "./data.js";
import { GLYPHS, glyph, h, icon, safeLink, stars, toast } from "./dom.js";

const FEATURED = 5;
const view = { category: "all", query: "" };
let rerender = () => {};

/** Called after any change the page makes, so every view draws again. */
export function onChange(callback) {
  rerender = callback;
}

function categoryOf(app) {
  return CATEGORY_LABELS[app.category] || "Apps";
}

function ranked(apps) {
  return [...apps].sort((a, b) => (b.picks - a.picks) || (b.installs - a.installs) || a.title.localeCompare(b.title));
}

function matches(app, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const text = [app.title, app.shortDescription, app.description, categoryOf(app), app.subcategory || "", app.publisherDisplayName]
    .join(" ")
    .toLowerCase();
  return words.every((word) => text.includes(word));
}

async function tapGet(app, button) {
  if (!state.live) {
    toast("This is a preview. Get works once Muse runs the App Store.");
    return;
  }
  button.disabled = true;
  try {
    await get(app);
    toast(`Muse installs ${app.title} at its next check.`);
    rerender({ pop: app.id });
  } catch (error) {
    toast(`${app.title} couldn't be added: ${error.message}`);
    button.disabled = false;
  }
}

async function tapCancel(app, event) {
  try {
    await cancel(event);
    toast(`${app.title} won't be installed.`);
  } catch (error) {
    toast(`Couldn't take it back: ${error.message}`);
  }
  rerender({});
}

/** The pill on a row or a page: Get, Waiting, Installing, Open, or Try again. */
export function getButton(app, { big = false, pop = false } = {}) {
  const current = stateOf(app);
  const classes = ["get"];
  if (big) classes.push("get-big");
  if (pop) classes.push("is-pop");
  const stop = (event) => event.stopPropagation();
  if (current.kind === "installed") {
    const href = safeLink(current.address);
    if (href) {
      classes.push("is-open");
      return h("a", { class: classes.join(" "), href, target: "_blank", rel: "noopener", onclick: stop, "aria-label": `Open ${app.title}` }, "Open");
    }
  }
  if (current.kind === "waiting") {
    classes.push("is-waiting");
    return h("button", { class: classes.join(" "), type: "button", disabled: true, "aria-label": `${app.title} is waiting for Muse` },
      glyph(GLYPHS.clock), "Waiting");
  }
  if (current.kind === "installing") {
    classes.push("is-waiting");
    return h("button", { class: classes.join(" "), type: "button", disabled: true, "aria-label": `Muse is installing ${app.title}` },
      h("span", { class: "spinner", "aria-hidden": "true" }), "Installing");
  }
  if (current.kind === "failed") {
    classes.push("is-failed");
    const retry = h("button", { class: classes.join(" "), type: "button", "aria-label": `Try ${app.title} again` }, "Try again");
    retry.addEventListener("click", (event) => { stop(event); tapGet(app, retry); });
    return retry;
  }
  const button = h("button", { class: classes.join(" "), type: "button", "aria-label": `Get ${app.title}` }, "Get");
  button.addEventListener("click", (event) => { stop(event); tapGet(app, button); });
  return button;
}

function metaLine(app) {
  const current = stateOf(app);
  if (current.kind === "installed") return h("span", { class: "row-meta meta-ok" }, "Installed");
  if (current.kind === "waiting") return h("span", { class: "row-meta meta-warn" }, "Waiting for Muse");
  if (current.kind === "installing") return h("span", { class: "row-meta meta-warn" }, "Muse is setting it up");
  if (current.kind === "failed") return h("span", { class: "row-meta meta-danger" }, "Didn't install");
  const rating = app.stars && app.stars.average ? `${app.stars.average.toFixed(1)} ★ · ` : "";
  return h("span", { class: "row-meta" }, `${rating}${categoryOf(app)}`);
}

function row(app, rank, pop) {
  return h("li", { class: "row", onclick: () => { location.hash = `#app/${app.id}`; } },
    h("span", { class: "row-rank", "aria-hidden": "true" }, rank ? String(rank) : ""),
    icon(app),
    h("span", { class: "row-words" },
      h("a", { class: "row-title", href: `#app/${app.id}`, onclick: (event) => event.stopPropagation() }, app.title),
      h("span", { class: "row-text" }, app.shortDescription),
      metaLine(app)),
    getButton(app, { pop: pop === app.id }));
}

function feature(app, pop) {
  const shot = (app.screenshotUrls || [])[0];
  return h("article", { class: "feature", onclick: () => { location.hash = `#app/${app.id}`; }, "aria-label": app.title },
    shot ? h("img", { class: "feature-shot", src: shot, alt: "", loading: "lazy", decoding: "async" }) : null,
    h("span", { class: "feature-fade", "aria-hidden": "true" }),
    h("span", { class: "feature-kicker" }, categoryOf(app)),
    h("div", { class: "feature-foot" },
      icon(app),
      h("div", {},
        h("p", { class: "feature-title" }, app.title),
        h("p", { class: "feature-text" }, app.shortDescription)),
      getButton(app, { pop: pop === app.id })));
}

function chips() {
  const present = new Set(state.store.apps.map((app) => app.category));
  const order = Object.keys(CATEGORY_LABELS).filter((id) => present.has(id));
  if (view.category !== "all" && !present.has(view.category)) view.category = "all";
  const list = document.getElementById("chips");
  list.replaceChildren(...[["all", "All"], ...order.map((id) => [id, CATEGORY_LABELS[id]])].map(([id, label]) =>
    h("button", {
      class: "chip",
      type: "button",
      role: "tab",
      "aria-selected": view.category === id ? "true" : "false",
      onclick: () => { view.category = id; rerender({}); document.getElementById("list-title").scrollIntoView({ block: "nearest" }); },
    }, label)));
}

function notice() {
  const el = document.getElementById("notice");
  let text = "";
  if (!state.live) text = "A preview with sample apps. Once Muse runs the App Store, this is the real store and Get works.";
  else if (!state.read) text = "Muse hasn't read the store yet. It reads it at its next check, or say \"install my apps\" to Muse.";
  else if (state.store.problem) text = `The store couldn't be read just now: ${state.store.problem} These are the apps from ${ago(state.store.readAt) || "the last read"}.`;
  el.textContent = text;
  el.hidden = text === "";
}

export function renderDiscover(pop) {
  document.getElementById("today").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  chips();
  notice();
  const all = ranked(state.store.apps);
  const query = view.query.trim();
  const inCategory = view.category === "all" ? all : all.filter((app) => app.category === view.category);
  const shown = query ? inCategory.filter((app) => matches(app, query)) : inCategory;
  const featured = !query && view.category === "all" ? shown.slice(0, FEATURED) : [];
  document.getElementById("featured").replaceChildren(...featured.map((app) => feature(app, pop)));
  const title = query ? "Results" : view.category === "all" ? "Top apps" : CATEGORY_LABELS[view.category];
  document.getElementById("list-title").textContent = title;
  document.getElementById("list-count").textContent = shown.length ? `${shown.length} ${shown.length === 1 ? "app" : "apps"}` : "";
  document.getElementById("list").replaceChildren(...shown.map((app, n) => row(app, query ? 0 : n + 1, pop)));
  const empty = document.getElementById("empty");
  empty.hidden = shown.length > 0 || !state.read;
  empty.textContent = query ? `Nothing matches "${query}". Try another word, or All.` : "No apps here yet.";
}

export function setQuery(query) {
  view.query = query;
}

export function renderYours(pop) {
  const updated = state.store.readAt ? `Updated ${ago(state.store.readAt)}` : "";
  document.getElementById("yours-updated").textContent = updated;
  const apps = ranked(state.store.apps);
  const groups = { waiting: [], failed: [], installed: [] };
  for (const app of apps) {
    const kind = stateOf(app).kind;
    if (kind === "waiting" || kind === "installing") groups.waiting.push(app);
    else if (kind === "failed") groups.failed.push(app);
    else if (kind === "installed") groups.installed.push(app);
  }
  for (const [name, list] of Object.entries(groups)) {
    document.getElementById(`yours-${name}`).replaceChildren(...list.map((app) => row(app, 0, pop)));
    document.getElementById(`yours-${name}-block`).hidden = list.length === 0;
  }
  document.getElementById("yours-empty").hidden = apps.some((app) => stateOf(app).kind !== "get");
}

export function renderBar() {
  const waiting = waitingApps();
  const bar = document.getElementById("waiting-bar");
  const badge = document.getElementById("yours-badge");
  bar.hidden = waiting.length === 0 || !document.getElementById("page").hidden;
  badge.hidden = waiting.length === 0;
  badge.textContent = String(waiting.length);
  if (waiting.length === 0) return;
  document.getElementById("waiting-count").textContent =
    waiting.length === 1 ? `${waiting[0].title} is waiting for Muse` : `${waiting.length} apps are waiting for Muse`;
  document.getElementById("waiting-hint").textContent =
    `Muse installs ${waiting.length === 1 ? "it" : "them"} at its next check. Say "install my apps" to start now.`;
}

function statusPanel(app) {
  const current = stateOf(app);
  if (current.kind === "get") return null;
  if (current.kind === "installed") {
    const href = safeLink(current.address);
    return h("section", { class: "status status-ok" },
      h("span", { class: "status-mark" }, glyph(GLYPHS.check)),
      h("div", { class: "status-words" },
        h("p", { class: "status-title" }, "Installed"),
        h("p", { class: "status-text" }, "Muse runs it for you at this link."),
        href ? h("a", { class: "status-link", href, target: "_blank", rel: "noopener" }, current.address) : null));
  }
  if (current.kind === "waiting") {
    const takeBack = h("button", { class: "btn btn-quiet", type: "button" }, "Don't install");
    takeBack.addEventListener("click", () => tapCancel(app, current.event));
    return h("section", { class: "status status-waiting" },
      h("span", { class: "status-mark" }, glyph(GLYPHS.clock)),
      h("div", { class: "status-words" },
        h("p", { class: "status-title" }, "Waiting for Muse"),
        h("p", { class: "status-text" }, "Muse installs it at its next check and puts its link here. Say \"install my apps\" to Muse to start now."),
        h("div", { class: "status-actions" }, takeBack)));
  }
  if (current.kind === "installing") {
    return h("section", { class: "status status-waiting" },
      h("span", { class: "status-mark" }, h("span", { class: "spinner", "aria-hidden": "true" })),
      h("div", { class: "status-words" },
        h("p", { class: "status-title" }, "Muse is setting it up"),
        h("p", { class: "status-text" }, "Its link shows up here once it runs.")));
  }
  return h("section", { class: "status status-failed" },
    h("span", { class: "status-mark" }, glyph(GLYPHS.alert)),
    h("div", { class: "status-words" },
      h("p", { class: "status-title" }, "Didn't install"),
      h("p", { class: "status-text" }, current.reason || "Muse couldn't install it."),
      h("p", { class: "status-text" }, "Try again, or ask Muse to remove it.")));
}

function stat(top, big, low) {
  return h("div", { class: "stat" },
    h("span", { class: "stat-top" }, top),
    h("span", { class: "stat-big" }, big),
    low);
}

/** The page of one app, drawn into the page layer. */
export function renderPage(app, pop) {
  const ratings = app.stars && app.stars.count ? app.stars.count : 0;
  const average = app.stars && app.stars.average ? app.stars.average : null;
  const shots = (app.screenshotUrls || []).map((src, n) => {
    const img = h("img", { class: "shot", src, alt: `${app.title}, screenshot ${n + 1}`, loading: "lazy", decoding: "async" });
    img.addEventListener("load", () => { if (img.naturalWidth > img.naturalHeight) img.classList.add("wide"); });
    return img;
  });
  const about = h("p", { class: "about-text clamped" }, app.description);
  const more = h("button", { class: "more", type: "button" }, "more");
  more.addEventListener("click", () => { about.classList.remove("clamped"); more.hidden = true; });
  more.hidden = app.description.length < 220;
  if (more.hidden) about.classList.remove("clamped");

  document.getElementById("page-bar-title").replaceChildren(icon(app), h("span", {}, app.title));
  document.getElementById("page-bar-action").replaceChildren(getButton(app));
  document.getElementById("page-body").replaceChildren(
    h("header", { class: "hero" },
      icon(app),
      h("div", { class: "hero-words" },
        h("h1", { class: "hero-title", id: "page-title" }, app.title),
        h("p", { class: "hero-sub" }, app.shortDescription),
        h("div", { class: "hero-actions" }, getButton(app, { big: true, pop: pop === app.id })))),
    h("div", { class: "stats" },
      stat(ratings ? `${count(ratings)} ratings` : "Ratings", average ? average.toFixed(1) : "None", stars(average)),
      stat("Installs", count(app.installs), h("span", { class: "stat-low" }, "on agents")),
      stat("Picks", count(app.picks), h("span", { class: "stat-low" }, "people")),
      stat("Category", categoryOf(app), h("span", { class: "stat-low" }, app.subcategory || ""))),
    statusPanel(app),
    shots.length ? h("div", { class: "shots", "aria-label": "Screenshots" }, shots) : null,
    h("section", { class: "about" },
      h("h2", { class: "block-title" }, "About"),
      about,
      more),
    h("section", { class: "about" },
      h("h2", { class: "block-title" }, "Information"),
      h("dl", { class: "facts" },
        h("div", { class: "fact" }, h("dt", {}, "Made by"), h("dd", {}, app.publisherDisplayName)),
        h("div", { class: "fact" }, h("dt", {}, "Category"), h("dd", {}, categoryOf(app))),
        app.subcategory ? h("div", { class: "fact" }, h("dt", {}, "Kind"), h("dd", {}, app.subcategory)) : null,
        h("div", { class: "fact" }, h("dt", {}, "Runs on"), h("dd", {}, "Muse, at a link of your own")))));
}
