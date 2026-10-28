// The floating chrome over the shelf: owner and tally, the view tabs, the sort menu, the light switch, the
// now-reading cards, the bay pager, the row stepper, the book label, and the one-time hint. DOM only, styled by the tokens.
import { SORTS } from "./state.js";
import { possessive, num } from "./format.js";

const $ = (id) => document.getElementById(id);
const SCHEME_KEY = "reading-shelf:scheme";

export function createHud(store, ctl) {
  const app = $("app");
  $("owner").textContent = possessive(store.owner);
  document.title = `${possessive(store.owner)} | Reading Shelf`;

  function tally() {
    const n = store.books.length;
    const read = store.books.filter((b) => b.status === "read").length;
    const going = store.books.filter((b) => b.status === "reading").length;
    const el = $("tally");
    if (!n) {
      el.textContent = "No books on this shelf yet.";
      return;
    }
    // The count always shows; the read and in-progress parts give way on the narrowest headers.
    const more = [];
    if (read) more.push(`${num(read)} read`);
    if (going) more.push(`${num(going)} in progress`);
    const extra = document.createElement("span");
    extra.className = "tally-more";
    extra.textContent = more.map((m) => `, ${m}`).join("");
    el.replaceChildren(`${num(n)} ${n === 1 ? "book" : "books"}`, extra);
  }

  // Views
  const tabs = [...document.querySelectorAll(".view-tab")];
  tabs.forEach((tab) => tab.addEventListener("click", () => ctl.setView(tab.dataset.view)));
  function showView(view) {
    tabs.forEach((tab) => tab.setAttribute("aria-pressed", String(tab.dataset.view === view)));
    app.dataset.view = view;
  }

  // Sort menu
  const sortButton = $("sort-button");
  const menu = $("sort-menu");
  let menuIndex = 0;
  function renderMenu() {
    menu.replaceChildren(
      ...SORTS.map((s, i) => {
        const li = document.createElement("li");
        li.setAttribute("role", "option");
        li.dataset.sort = s.id;
        li.id = `sort-${s.id}`;
        li.textContent = s.label;
        li.setAttribute("aria-selected", String(s.id === store.sort));
        li.classList.toggle("is-active", i === menuIndex);
        li.addEventListener("click", () => {
          closeMenu();
          ctl.setSort(s.id);
        });
        return li;
      }),
    );
    const current = SORTS.find((s) => s.id === store.sort);
    $("sort-label").textContent = current.label;
    sortButton.setAttribute("aria-label", `Sort: ${current.label}`);
  }
  function openMenu() {
    menuIndex = Math.max(0, SORTS.findIndex((s) => s.id === store.sort));
    renderMenu();
    menu.hidden = false;
    sortButton.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => menu.classList.add("is-open"));
    menu.setAttribute("aria-activedescendant", `sort-${SORTS[menuIndex].id}`);
  }
  function closeMenu() {
    if (menu.hidden) return;
    menu.classList.remove("is-open");
    sortButton.setAttribute("aria-expanded", "false");
    setTimeout(() => {
      if (!menu.classList.contains("is-open")) menu.hidden = true;
    }, 180);
  }
  sortButton.addEventListener("click", (e) => {
    e.stopPropagation();
    if (menu.hidden) openMenu();
    else closeMenu();
  });
  sortButton.addEventListener("keydown", (e) => {
    if (menu.hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      menuIndex = (menuIndex + (e.key === "ArrowDown" ? 1 : -1) + SORTS.length) % SORTS.length;
      renderMenu();
      menu.setAttribute("aria-activedescendant", `sort-${SORTS[menuIndex].id}`);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      closeMenu();
      ctl.setSort(SORTS[menuIndex].id);
    }
  });
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target)) closeMenu();
  });

  // Light switch: follows the system until the person picks.
  const scheme = $("scheme");
  const dark = () => {
    const forced = document.documentElement.getAttribute("data-theme");
    if (forced) return forced === "dark";
    return matchMedia("(prefers-color-scheme: dark)").matches;
  };
  function syncScheme() {
    const isDark = dark();
    scheme.dataset.scheme = isDark ? "dark" : "light";
    scheme.setAttribute("aria-label", isDark ? "Switch to daylight" : "Switch to lamplight");
  }
  scheme.addEventListener("click", () => {
    const next = dark() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(SCHEME_KEY, next);
    } catch {
      // The switch still holds for this visit.
    }
    syncScheme();
    ctl.themeChanged();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    syncScheme();
    ctl.themeChanged();
  });

  // Now reading
  const now = $("now");
  function renderNow(thumb) {
    const reading = store.books.filter((b) => b.status === "reading").slice(0, 2);
    now.replaceChildren(
      ...reading.map((b) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "now-card";
        const c = document.createElement("canvas");
        c.className = "now-thumb";
        c.width = 88;
        c.height = 132;
        thumb(b.id, c);
        const textBox = document.createElement("span");
        textBox.className = "now-text";
        const pct = b.pages ? b.page / b.pages : 0;
        const kicker = document.createElement("span");
        kicker.className = "now-kicker";
        kicker.textContent = "Reading now";
        const title = document.createElement("span");
        title.className = "now-title";
        title.textContent = b.title;
        const page = document.createElement("span");
        page.className = "now-page";
        page.textContent = b.pages ? `Page ${num(b.page)} of ${num(b.pages)}` : b.author;
        const bar = document.createElement("span");
        bar.className = "now-bar";
        const fill = document.createElement("span");
        fill.style.setProperty("--p", String(pct));
        bar.append(fill);
        textBox.append(kicker, title, page, bar);
        card.append(c, textBox);
        card.setAttribute("aria-label", `Open ${b.title}, page ${b.page} of ${b.pages}`);
        card.addEventListener("click", () => ctl.open(b.id));
        return card;
      }),
    );
  }

  // Rows (one-row screens)
  const rows = $("rows");
  const dots = $("row-dots");
  $("row-up").addEventListener("click", () => ctl.stepRow(-1));
  $("row-down").addEventListener("click", () => ctl.stepRow(1));
  function renderRows(count, current, visible) {
    rows.hidden = !visible;
    if (!visible) return;
    if (dots.children.length !== count) dots.replaceChildren(...Array.from({ length: count }, () => document.createElement("li")));
    [...dots.children].forEach((li, i) => (li.dataset.on = String(i === current)));
    $("row-up").disabled = current <= 0;
    $("row-down").disabled = current >= count - 1;
  }

  // Bays (a phone held upright frames one bay at a time)
  const bays = $("bays");
  const bayDots = $("bay-dots");
  $("bay-left").addEventListener("click", () => ctl.stepBay(-1));
  $("bay-right").addEventListener("click", () => ctl.stepBay(1));
  function renderBays(count, current, elsewhere, visible) {
    bays.hidden = !visible || count < 2;
    if (bays.hidden) return;
    if (bayDots.children.length !== count) bayDots.replaceChildren(...Array.from({ length: count }, () => document.createElement("li")));
    [...bayDots.children].forEach((li, i) => (li.dataset.on = String(i === current)));
    $("bay-label").textContent = elsewhere ? `${num(elsewhere)} more ${elsewhere === 1 ? "book" : "books"}` : `Bay ${current + 1} of ${count}`;
    $("bay-left").disabled = current <= 0;
    $("bay-right").disabled = current >= count - 1;
  }

  // Book label
  const tip = $("tip");
  let tipFor = null;
  function showTip(book, words) {
    if (!book) {
      tip.classList.remove("is-on");
      tipFor = null;
      return;
    }
    if (tipFor !== book.id) {
      $("tip-title").textContent = book.title;
      $("tip-meta").textContent = words;
      tipFor = book.id;
    }
    tip.hidden = false;
    tip.classList.add("is-on");
  }
  function placeTip(x, y) {
    tip.style.setProperty("--x", `${Math.round(x)}px`);
    tip.style.setProperty("--y", `${Math.round(y)}px`);
  }

  // Hint
  const hint = $("hint");
  let hintTimer = 0;
  function showHint(textValue) {
    hint.textContent = textValue;
    hint.hidden = false;
    hint.classList.remove("is-gone");
    clearTimeout(hintTimer);
    hintTimer = setTimeout(hideHint, 6000);
  }
  function hideHint() {
    hint.classList.add("is-gone");
  }

  tally();
  renderMenu();
  syncScheme();
  return { tally, showView, renderMenu, closeMenu, menuOpen: () => !menu.hidden, renderNow, renderRows, renderBays, showTip, placeTip, showHint, hideHint };
}
