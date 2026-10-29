// The routes (#discover, #yours, #app/<id>), the search box, and the refresh every few seconds.
import { connect, load, state } from "./data.js";
import { onChange, renderBar, renderDiscover, renderPage, renderYours, setQuery } from "./views.js";

const POLL_MS = 5000;
const page = document.getElementById("page");
const scroller = document.getElementById("page-scroll");
let lastTab = "discover";
let openApp = null;

function route() {
  const hash = location.hash.replace(/^#/, "");
  if (hash.startsWith("app/")) return { tab: lastTab, appId: decodeURIComponent(hash.slice(4)) };
  return { tab: hash === "yours" ? "yours" : "discover", appId: null };
}

function draw(options = {}) {
  const { tab, appId } = route();
  lastTab = tab;
  document.getElementById("view-discover").hidden = tab !== "discover";
  document.getElementById("view-yours").hidden = tab !== "yours";
  for (const link of document.querySelectorAll(".tab")) {
    if (link.dataset.tab === tab) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  renderDiscover(options.pop);
  renderYours(options.pop);
  const app = appId ? state.store.apps.find((entry) => entry.id === appId) : null;
  if (app) {
    const fresh = openApp !== app.id;
    renderPage(app, options.pop);
    if (fresh) {
      page.classList.remove("leaving", "scrolled");
      page.hidden = false;
      scroller.scrollTop = 0;
      scroller.focus({ preventScroll: true });
    }
    openApp = app.id;
  } else if (openApp !== null) {
    openApp = null;
    page.classList.add("leaving");
    setTimeout(() => {
      if (openApp === null) {
        page.hidden = true;
        page.classList.remove("leaving");
        renderBar();
      }
    }, 220);
  }
  renderBar();
}

onChange(draw);

document.getElementById("page-back").addEventListener("click", () => {
  location.hash = `#${lastTab}`;
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !page.hidden) location.hash = `#${lastTab}`;
});
scroller.addEventListener("scroll", () => {
  page.classList.toggle("scrolled", scroller.scrollTop > 120);
}, { passive: true });

const search = document.getElementById("search");
const clear = document.getElementById("search-clear");
search.addEventListener("input", () => {
  setQuery(search.value);
  clear.hidden = search.value === "";
  draw();
});
clear.addEventListener("click", () => {
  search.value = "";
  setQuery("");
  clear.hidden = true;
  search.focus();
  draw();
});

window.addEventListener("hashchange", () => draw());

async function tick() {
  if (state.live && document.visibilityState === "visible") {
    try {
      await load();
      draw();
    } catch {
      // A missed read leaves the page as it was; the next tick tries again.
    }
  }
  setTimeout(tick, POLL_MS);
}

await connect();
draw();
setTimeout(tick, POLL_MS);
