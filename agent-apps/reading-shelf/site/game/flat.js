// The flat shelf for a browser without WebGL or a phone too small for the 3D one: spines as CSS 3D blocks with
// preserve-3d, painted by the same canvas hands, tilting out on hover or tap and opening as two pages.
import { atlasLayout, paintAtlas, paintThumb, dominantColor, hash } from "../scene/textures.js";
import { bookDims } from "../scene/dims.js";
import { readTokens } from "../scene/tokens.js";
import { statusWords } from "./format.js";

const PX = 1000;

function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

export function createFlat(store, ctl) {
  const root = document.getElementById("flat");
  root.hidden = false;
  let tokens = readTokens();
  const art = new Map();
  let reading = null;
  let focusedId = null;

  const palette = () => ({ paper: tokens.paper, ink: tokens.ink, pageAccent: tokens.pageAccent, books: tokens.books });

  function paint(b) {
    const a = art.get(b.id);
    const color = a.image ? a.color : tokens.books[hash(b.id) % tokens.books.length];
    paintAtlas(a.canvas, b, a.layout, { color, image: a.image, palette: palette() });
    const { spine, cover } = a.layout;
    for (const [el, r] of [
      [a.spineCanvas, spine],
      [a.coverCanvas, cover],
    ]) {
      el.width = r.w;
      el.height = r.h;
      el.getContext("2d").drawImage(a.canvas, r.x, r.y, r.w, r.h, 0, 0, r.w, r.h);
    }
  }

  const wall = document.createElement("div");
  wall.className = "flat-wall";
  root.append(wall);

  store.books.forEach((b) => {
    const dims = bookDims(b);
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const el = document.createElement("button");
    el.type = "button";
    el.className = "flat-book";
    el.setAttribute("aria-label", `${b.title} by ${b.author}`);
    el.style.setProperty("--t", `${Math.round(dims.t * PX * 0.8)}px`);
    el.style.setProperty("--h", `${Math.round(dims.h * PX * 0.8)}px`);
    el.style.setProperty("--d", `${Math.round(dims.d * PX * 0.8)}px`);
    const spineCanvas = document.createElement("canvas");
    spineCanvas.className = "flat-spine";
    const coverCanvas = document.createElement("canvas");
    coverCanvas.className = "flat-cover";
    el.append(spineCanvas, coverCanvas);
    el.addEventListener("click", () => {
      if (focusedId === b.id || matchMedia("(hover: hover)").matches) ctl.open(b.id);
      else {
        focusedId = b.id;
        root.querySelectorAll(".flat-book").forEach((n) => n.classList.toggle("is-out", n === el));
      }
    });
    art.set(b.id, { el, canvas, layout: atlasLayout(dims, 512), spineCanvas, coverCanvas, image: null, color: null });
  });

  const opened = document.createElement("div");
  opened.className = "flat-open";
  opened.hidden = true;
  opened.innerHTML = '<div class="flat-page flat-left"></div><div class="flat-page flat-right"></div>';
  root.append(opened);

  function layout() {
    const rows = [[], [], []];
    const sorted = store.sorted();
    sorted.forEach((b, i) => rows[Math.min(2, Math.floor((i * 3) / Math.max(1, sorted.length)))].push(b));
    wall.replaceChildren(
      ...rows.map((list) => {
        const row = document.createElement("div");
        row.className = "flat-row";
        list.forEach((b) => {
          const a = art.get(b.id);
          a.el.classList.toggle("is-face", b.status === "reading");
          row.append(a.el);
        });
        return row;
      }),
    );
  }

  Promise.all(
    store.books.map(async (b) => {
      const a = art.get(b.id);
      if (b.cover) a.image = await loadImage(b.cover);
      a.color = (a.image && dominantColor(a.image)) || tokens.books[hash(b.id) % tokens.books.length];
      paint(b);
    }),
  ).then(() => ctl.themeChanged());
  layout();

  return {
    get reading() {
      return reading;
    },
    layout,
    thumb(id, target) {
      const a = art.get(id);
      if (a) paintThumb(target, a.canvas, a.layout);
    },
    applyTheme() {
      tokens = readTokens();
      store.books.forEach(paint);
    },
    open(id) {
      const b = store.byId(id);
      reading = id;
      const [left, right] = opened.children;
      left.replaceChildren();
      right.replaceChildren();
      const h = document.createElement("h3");
      h.textContent = b.title;
      const au = document.createElement("p");
      au.className = "flat-author";
      au.textContent = b.author;
      const st = document.createElement("p");
      st.className = "flat-status";
      st.textContent = statusWords(b);
      left.append(h, au, st);
      const note = document.createElement("p");
      note.className = "flat-note";
      note.textContent = b.note || "No note yet.";
      right.append(note);
      opened.hidden = false;
      requestAnimationFrame(() => opened.classList.add("is-open"));
    },
    close() {
      reading = null;
      opened.classList.remove("is-open");
      setTimeout(() => {
        if (!opened.classList.contains("is-open")) opened.hidden = true;
      }, 400);
    },
  };
}
