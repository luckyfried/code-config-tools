// The chip row: one chip per habit with its own small ring; a tap closes a plain habit or adds one to a countable one.
import { glyph, icon } from "./icons.js";

const NS = "http://www.w3.org/2000/svg";

function miniRing() {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 40 40");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML =
    '<g transform="rotate(-90 20 20)"><circle class="track" cx="20" cy="20" r="18"/>' +
    '<circle class="arc is-empty" cx="20" cy="20" r="18" pathLength="100"/></g>';
  return svg;
}

export function createChips({ root, habits, onTap, onLess, reduced }) {
  const items = habits.map((habit, i) => {
    const li = document.createElement("li");
    li.className = "chip";
    li.style.setProperty("--hue", `var(--habit-${i + 1})`);

    const main = document.createElement("button");
    main.type = "button";
    main.className = "chip-main";

    const ring = document.createElement("span");
    ring.className = "chip-ring";
    const svg = miniRing();
    const mark = document.createElement("span");
    mark.className = "glyph";
    mark.append(glyph(habit));
    ring.append(svg, mark);

    const text = document.createElement("span");
    text.className = "chip-text";
    const label = document.createElement("span");
    label.className = "chip-label";
    label.textContent = habit.label;
    const sub = document.createElement("span");
    sub.className = "chip-sub";
    text.append(label, sub);

    const key = document.createElement("kbd");
    key.className = "chip-key";
    key.textContent = String(i + 1);
    key.setAttribute("aria-hidden", "true");

    main.append(ring, text, key);
    main.addEventListener("click", () => onTap(i));
    li.append(main);

    let less = null;
    if (habit.target) {
      less = document.createElement("button");
      less.type = "button";
      less.className = "chip-less";
      less.setAttribute("aria-label", `One less ${habit.label}`);
      const minus = icon("check");
      minus.innerHTML = '<path d="M6 12h12"/>';
      less.append(minus);
      less.addEventListener("click", () => onLess(i));
      li.append(less);
    }
    root.append(li);
    return { li, main, sub, arc: svg.querySelector(".arc"), ring, less };
  });

  /** Shows each habit's count for the day on its chip. */
  function set(counts) {
    habits.forEach((habit, i) => {
      const item = items[i];
      const count = counts[i];
      const target = habit.target || 1;
      const closed = count >= target;
      const p = count / target;
      item.li.classList.toggle("is-closed", closed);
      item.arc.style.setProperty("--offset", String(Math.round((1 - p) * 1000) / 10));
      item.arc.classList.toggle("is-empty", p <= 0);
      if (habit.target) {
        item.sub.textContent = `${count} of ${habit.target}`;
        item.main.setAttribute("aria-label", `${habit.label}, ${count} of ${habit.target}. Add one.`);
        item.less.hidden = count === 0;
      } else {
        item.sub.textContent = closed ? "Closed" : "Tap to close";
        item.main.setAttribute("aria-pressed", String(closed));
        item.main.setAttribute("aria-label", habit.label);
      }
    });
  }

  function pop(i) {
    if (reduced()) return;
    items[i].ring.animate(
      [{ transform: "scale(1)" }, { transform: "scale(1.14)", offset: 0.4 }, { transform: "scale(1)" }],
      { duration: 480, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
    );
  }

  return { set, pop };
}
