// By category: one horizontal bar per category, built from a segment per service in its own color, longest first.

import { bright, listJoin } from "./format.js";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function createCategories({ root, note, subs, categories, money }) {
  const groups = categories.map((name) => {
    const members = subs.filter((s) => s.category === name).sort((a, b) => b.yearlyCents - a.yearlyCents);
    return { name, members, cents: members.reduce((sum, s) => sum + s.yearlyCents, 0) };
  });
  groups.sort((a, b) => b.cents - a.cents || a.name.localeCompare(b.name));
  const max = Math.max(1, ...groups.map((g) => g.cents));
  const all = groups.reduce((sum, g) => sum + g.cents, 0);
  let revealed = false;

  const rows = groups.map((g) => {
    const li = el("li", `cat${g.members.length ? "" : " is-empty"}`);
    const name = el("h3", "cat-name", g.name);
    const total = el("p", "cat-total");
    const track = el("div", "cat-track");
    const bar = el("div", "cat-bar");
    bar.style.setProperty("--share", (g.cents / max).toFixed(4));
    const segs = g.members.map((s) => {
      const seg = el("span", `cat-seg hued${bright(s.hue) ? " is-bright" : ""}`);
      seg.style.setProperty("--hue", String(s.hue));
      seg.style.setProperty("--grow", String(s.yearlyCents));
      seg.title = `${s.name}, ${money.cents(s.yearlyCents)} a year`;
      bar.append(seg);
      return { seg, s };
    });
    track.append(bar);
    track.setAttribute("aria-hidden", "true");
    const names = el("p", "cat-names", g.members.length ? listJoin(g.members.map((s) => s.name)) : "Nothing here yet.");
    li.append(name, total, track, names);
    root.append(li);
    return { g, total, bar, segs };
  });

  function update(off) {
    let kept = 0;
    for (const r of rows) {
      const cents = r.g.members.reduce((sum, s) => sum + (off.has(s.id) ? 0 : s.yearlyCents), 0);
      kept += cents;
      const share = all ? Math.round((r.g.cents / all) * 100) : 0;
      const sub = el("span", "", cents === r.g.cents ? ` a year, ${share}%` : ` a year, from ${money.cents(r.g.cents)}`);
      r.total.replaceChildren(money.cents(cents), sub);
      for (const { seg, s } of r.segs) seg.classList.toggle("is-off", off.has(s.id));
    }
    const top = rows.find((r) => r.g.cents > 0);
    if (top) {
      const strong = el("strong", "", top.g.name);
      note.replaceChildren(strong, ` costs the most, ${money.cents(top.g.cents)} of ${money.cents(all)} a year.`);
    } else {
      note.textContent = "No categories have a subscription yet.";
    }
    return kept;
  }

  // Draws each bar in from the left the first time the screen opens.
  function reveal() {
    if (revealed) return;
    revealed = true;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    rows.forEach((r, i) => {
      r.bar.animate(
        [{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }],
        { duration: 700, delay: i * 50, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
      );
    });
  }

  return { update, reveal };
}
