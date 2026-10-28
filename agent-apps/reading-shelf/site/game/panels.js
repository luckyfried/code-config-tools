// The open book's details, the List panel, and the Stats panel.
import { num, longDate, monthShort, monthName, parseDate } from "./format.js";

const $ = (id) => document.getElementById(id);
const STAR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.8l2.75 5.86 6.4.74-4.74 4.36 1.27 6.32L12 16.9l-5.68 3.18 1.27-6.32L2.85 9.4l6.4-.74z"/></svg>';

export function reveal(el) {
  el.hidden = false;
  void el.offsetWidth;
  el.classList.add("is-open");
}

export function conceal(el) {
  el.classList.remove("is-open");
  setTimeout(() => {
    if (!el.classList.contains("is-open")) el.hidden = true;
  }, 340);
}

function starButtons(container, value, onPick, small) {
  container.classList.toggle("stars-small", Boolean(small));
  if (container.children.length !== 5) {
    container.replaceChildren(
      ...[1, 2, 3, 4, 5].map((n) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "star";
        b.setAttribute("role", "radio");
        b.setAttribute("aria-label", `${n} ${n === 1 ? "star" : "stars"}`);
        b.innerHTML = STAR;
        b.dataset.n = String(n);
        return b;
      }),
    );
  }
  [...container.children].forEach((b) => {
    const n = Number(b.dataset.n);
    b.dataset.on = String(n <= value);
    b.setAttribute("aria-checked", String(n === value));
    b.onclick = (e) => {
      e.stopPropagation();
      onPick(n === value ? 0 : n);
    };
  });
}

function statusButtons(container, status, onPick) {
  [...container.querySelectorAll("button")].forEach((b) => {
    b.setAttribute("aria-checked", String(b.dataset.status === status));
    b.onclick = (e) => {
      e.stopPropagation();
      onPick(b.dataset.status);
    };
  });
}

export function createReader(store, ctl) {
  const el = $("reader");
  let id = null;
  $("reader-close").addEventListener("click", () => ctl.close());
  const pageInput = $("reader-page");
  const range = $("reader-range");
  pageInput.addEventListener("change", () => {
    const v = Math.max(0, Math.round(Number(pageInput.value) || 0));
    store.update(id, { page: v });
  });
  range.addEventListener("input", () => {
    const b = store.byId(id);
    if (!b || !b.pages) return;
    const v = Math.round((Number(range.value) / 100) * b.pages);
    pageInput.value = String(v);
    range.style.setProperty("--fill", `${range.value}%`);
  });
  range.addEventListener("change", () => {
    const b = store.byId(id);
    if (!b) return;
    store.update(id, { page: Math.round((Number(range.value) / 100) * b.pages) });
  });

  function fill() {
    const b = store.byId(id);
    if (!b) return;
    $("reader-title").textContent = b.title;
    $("reader-author").textContent = b.author;
    statusButtons($("reader-status"), b.status, (status) => store.update(id, { status }));
    starButtons($("reader-stars"), b.rating, (rating) => store.update(id, { rating }));
    const prog = $("reader-progress");
    prog.hidden = b.status !== "reading" || !b.pages;
    if (!prog.hidden) {
      if (document.activeElement !== pageInput) pageInput.value = String(b.page);
      pageInput.max = String(b.pages);
      $("reader-of").textContent = `of ${num(b.pages)}`;
      const pct = Math.round((b.page / b.pages) * 100);
      range.value = String(pct);
      range.style.setProperty("--fill", `${pct}%`);
    }
    $("reader-note").textContent = b.note;
    const facts = [];
    if (b.pages) facts.push(["Length", `${num(b.pages)} pages`]);
    if (b.started) facts.push(["Started", longDate(b.started)]);
    if (b.finished && b.status === "read") facts.push(["Finished", longDate(b.finished)]);
    $("reader-facts").replaceChildren(
      ...facts.flatMap(([k, v]) => {
        const dt = document.createElement("dt");
        dt.textContent = k;
        const dd = document.createElement("dd");
        dd.textContent = v;
        return [dt, dd];
      }),
    );
  }

  return {
    get id() {
      return id;
    },
    open(bookId) {
      id = bookId;
      fill();
      reveal(el);
    },
    close() {
      id = null;
      conceal(el);
    },
    refresh() {
      if (id) fill();
    },
  };
}

export function createList(store, ctl, thumb) {
  const el = $("list");
  const list = $("book-list");
  const search = $("search");
  const filters = $("filters");
  let filter = "all";
  const FILTERS = [
    ["all", "All"],
    ["reading", "Reading"],
    ["read", "Read"],
    ["want", "Want to read"],
  ];

  function renderFilters() {
    filters.replaceChildren(
      ...FILTERS.map(([key, label]) => {
        const count = key === "all" ? store.books.length : store.books.filter((b) => b.status === key).length;
        const b = document.createElement("button");
        b.type = "button";
        b.className = "filter";
        b.setAttribute("role", "radio");
        b.setAttribute("aria-checked", String(filter === key));
        b.textContent = `${label} ${count}`;
        b.addEventListener("click", () => {
          filter = key;
          render();
        });
        return b;
      }),
    );
  }

  function render() {
    renderFilters();
    const q = search.value.trim().toLowerCase();
    const books = store.sorted().filter((b) => (filter === "all" || b.status === filter) && (!q || `${b.title} ${b.author} ${b.note}`.toLowerCase().includes(q)));
    if (!books.length) {
      const p = document.createElement("li");
      p.className = "list-empty";
      p.textContent = q ? `Nothing on the shelf matches “${search.value.trim()}”.` : "No books here yet.";
      list.replaceChildren(p);
      return;
    }
    list.replaceChildren(
      ...books.map((b) => {
        const li = document.createElement("li");
        li.className = "book-row";
        const c = document.createElement("canvas");
        c.className = "row-thumb";
        c.width = 104;
        c.height = 156;
        thumb(b.id, c);
        const open = document.createElement("button");
        open.type = "button";
        open.className = "row-open";
        const t = document.createElement("span");
        t.className = "row-title";
        t.textContent = b.title;
        const a = document.createElement("span");
        a.className = "row-author";
        a.textContent = b.author;
        open.append(t, a);
        open.addEventListener("click", () => ctl.open(b.id));
        const edit = document.createElement("div");
        edit.className = "row-edit";
        const seg = document.createElement("div");
        seg.className = "segmented";
        seg.setAttribute("role", "radiogroup");
        seg.setAttribute("aria-label", `Status of ${b.title}`);
        [
          ["read", "Read"],
          ["reading", "Reading"],
          ["want", "Want"],
        ].forEach(([s, label]) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.setAttribute("role", "radio");
          btn.dataset.status = s;
          btn.textContent = label;
          seg.append(btn);
        });
        statusButtons(seg, b.status, (status) => store.update(b.id, { status }));
        const stars = document.createElement("div");
        stars.className = "stars";
        stars.setAttribute("role", "radiogroup");
        stars.setAttribute("aria-label", `Rating of ${b.title}`);
        starButtons(stars, b.rating, (rating) => store.update(b.id, { rating }), true);
        edit.append(seg, stars);
        if (b.status === "reading" && b.pages) {
          const pg = document.createElement("span");
          pg.className = "row-page";
          pg.textContent = `Page ${num(b.page)} of ${num(b.pages)}`;
          edit.append(pg);
        }
        li.append(c, open, edit);
        return li;
      }),
    );
  }

  search.addEventListener("input", render);
  $("export").addEventListener("click", () => {
    const blob = new Blob([store.exportJSON()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reading-shelf-changes.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  $("import").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      const n = store.importJSON(await file.text());
      ctl.say(n ? `Brought in changes for ${n} ${n === 1 ? "book" : "books"}.` : "That file matches no book on this shelf.");
    } catch {
      ctl.say("That file is not a shelf export.");
    }
    e.target.value = "";
  });

  return {
    open() {
      render();
      reveal(el);
    },
    close() {
      conceal(el);
    },
    render,
    get isOpen() {
      return !el.hidden;
    },
  };
}

/** Twelve months of reading ending with the month of the latest finish: pages as bars, books as dots. */
export function createStats(store, ctl) {
  const el = $("stats");

  function render() {
    const finished = store.books.filter((b) => b.status === "read" && parseDate(b.finished));
    let end = new Date();
    if (finished.length) {
      const last = finished.map((b) => parseDate(b.finished)).sort((a, b) => b.y - a.y || b.m - a.m)[0];
      end = new Date(last.y, last.m, 1);
    }
    const months = [];
    for (let i = 11; i >= 0; i -= 1) {
      const d = new Date(end.getFullYear(), end.getMonth() - i, 1);
      months.push({ y: d.getFullYear(), m: d.getMonth(), pages: 0, books: [] });
    }
    for (const b of finished) {
      const p = parseDate(b.finished);
      const slot = months.find((mm) => mm.y === p.y && mm.m === p.m);
      if (slot) {
        slot.pages += b.pages;
        slot.books.push(b);
      }
    }
    const max = Math.max(1, ...months.map((m) => m.pages));
    const yearBooks = months.reduce((s, m) => s + m.books.length, 0);
    const yearPages = months.reduce((s, m) => s + m.pages, 0);
    const rated = store.books.filter((b) => b.rating > 0);
    const avg = rated.length ? rated.reduce((s, b) => s + b.rating, 0) / rated.length : 0;
    const going = store.books.filter((b) => b.status === "reading");
    const want = store.books.filter((b) => b.status === "want").length;

    const totals = document.createElement("div");
    totals.className = "stat-totals";
    const big = (value, label, cls = "stat-big") => {
      const wrap = document.createElement("div");
      const v = document.createElement("p");
      v.className = cls;
      v.textContent = value;
      const l = document.createElement("p");
      l.className = "stat-label";
      l.textContent = label;
      wrap.append(v, l);
      return wrap;
    };
    totals.append(big(num(yearBooks), yearBooks === 1 ? "book finished in twelve months" : "books finished in twelve months"), big(num(yearPages), "pages turned"));
    const pair = document.createElement("div");
    pair.className = "stat-pair";
    pair.append(big(avg ? avg.toFixed(1) : "None", "average rating", "stat-mid"), big(num(going.length), "on the go", "stat-mid"), big(num(want), "waiting", "stat-mid"));
    totals.append(pair);

    const chart = document.createElement("div");
    chart.className = "chart";
    const head = document.createElement("div");
    head.className = "chart-head";
    const title = document.createElement("p");
    title.className = "chart-title";
    title.textContent = `${monthName(months[0].m)} ${months[0].y} to ${monthName(months[11].m)} ${months[11].y}`;
    const key = document.createElement("p");
    key.className = "chart-key";
    key.innerHTML = '<span><i class="key-bar"></i>Pages</span><span><i class="key-dot"></i>Books</span>';
    head.append(title, key);
    const grid = document.createElement("div");
    grid.className = "months";
    grid.setAttribute("role", "img");
    grid.setAttribute("aria-label", months.map((m) => `${monthName(m.m)}: ${m.books.length} books, ${m.pages} pages`).join("; "));
    months.forEach((m, i) => {
      const col = document.createElement("div");
      col.className = "month";
      const plot = document.createElement("div");
      plot.className = "month-plot";
      const bar = document.createElement("div");
      bar.className = `month-bar${m.pages ? "" : " is-zero"}`;
      bar.style.setProperty("--d", `${i * 35}ms`);
      bar.title = m.books.map((b) => b.title).join(", ");
      plot.append(bar);
      if (m.pages) {
        const lab = document.createElement("span");
        lab.className = "month-pages";
        lab.textContent = num(m.pages);
        lab.style.setProperty("--h", String(m.pages / max));
        plot.append(lab);
      }
      const dots = document.createElement("div");
      dots.className = "month-books";
      m.books.forEach(() => dots.append(document.createElement("i")));
      const name = document.createElement("p");
      name.className = "month-name";
      name.textContent = monthShort(m.m);
      col.append(plot, dots, name);
      grid.append(col);
      requestAnimationFrame(() => requestAnimationFrame(() => bar.style.setProperty("--h", String(m.pages / max))));
    });
    chart.append(head, grid);

    const close = document.createElement("button");
    close.type = "button";
    close.className = "icon-button stats-close";
    close.setAttribute("aria-label", "Close stats");
    close.innerHTML = '<svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M5.5 5.5l9 9M14.5 5.5l-9 9"/></svg>';
    close.addEventListener("click", () => ctl.setView("shelf"));
    el.replaceChildren(totals, chart, close);
  }

  return {
    open() {
      render();
      reveal(el);
    },
    close() {
      conceal(el);
    },
    render,
    get isOpen() {
      return !el.hidden;
    },
  };
}
