// Small DOM helpers. Every text a person or the store wrote goes in through textContent, never as markup.

const SVG = "http://www.w3.org/2000/svg";

/** An element with attributes and children; a string child is text, null and false are skipped. */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") el.className = value;
    else if (name.startsWith("on") && typeof value === "function") el.addEventListener(name.slice(2), value);
    else if (value === true) el.setAttribute(name, "");
    else el.setAttribute(name, String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** An inline icon from path data, drawn with the current text color. */
export function glyph(paths, className = "") {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  if (className) svg.setAttribute("class", className);
  for (const d of paths) {
    const path = document.createElementNS(SVG, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

export const GLYPHS = {
  check: ["M5 12.5l4.5 4.5L19 7.5"],
  clock: ["M12 7v5l3 2", "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18"],
  alert: ["M12 8v5", "M12 16.5v.01", "M10.3 4.2L2.8 17.5a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"],
  open: ["M14 4h6v6", "M20 4l-9 9", "M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"],
  star: ["M12 2.8l2.8 5.8 6.3.9-4.6 4.4 1.1 6.3L12 17.2l-5.6 3 1.1-6.3L2.9 9.5l6.3-.9z"],
};

/** Five stars filled to `average` (1 to 5), drawn in the muted color. */
export function stars(average) {
  const row = h("span", { class: "stars", "aria-hidden": "true" });
  for (let n = 1; n <= 5; n += 1) {
    const star = glyph(GLYPHS.star, average !== null && n <= Math.round(average) ? "" : "off");
    row.append(star);
  }
  return row;
}

/** An app's icon; a store address or a file of this page. */
export function icon(app, size = "") {
  return h("img", {
    class: `icon ${size}`.trim(),
    src: app.iconUrl,
    alt: "",
    width: 64,
    height: 64,
    loading: "lazy",
    decoding: "async",
  });
}

/** An address a person may open: http or https only. */
export function safeLink(address) {
  try {
    const url = new URL(address);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

let toastTimer = 0;
/** One short line at the top of the screen for a few seconds. */
export function toast(text) {
  const el = document.getElementById("toast");
  el.textContent = text;
  el.classList.add("shown");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("shown"), 3200);
}
