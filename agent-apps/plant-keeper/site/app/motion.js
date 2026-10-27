// The few moving parts: the droplet and ripple, the rolling count, and the room underline.
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
export const calm = () => reduced.matches;

const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const FALL = "cubic-bezier(0.55, 0, 1, 0.45)";

/** Drops water into the pot: a 380 ms fall, a short squash, and a ripple across the soil. Resolves at the splash. */
export function dropWater(svg) {
  const drop = svg.querySelector(".drop");
  const ripple = svg.querySelector(".ripple");
  if (!drop || !ripple || calm()) return Promise.resolve();
  drop.animate(
    [
      { opacity: 0, transform: "translateY(-6px)" },
      { opacity: 1, transform: "translateY(0px)", offset: 0.12 },
      { opacity: 1, transform: "translateY(42px)" },
    ],
    { duration: 380, easing: FALL },
  ).finished.then(() => {
    drop.animate(
      [
        { opacity: 1, transform: "translateY(42px) scale(1, 1)" },
        { opacity: 0, transform: "translateY(45px) scale(1.5, 0.35)" },
      ],
      { duration: 140, easing: EASE_OUT },
    );
  });
  ripple.animate(
    [
      { opacity: 0, transform: "scale(0.3)" },
      { opacity: 0.95, transform: "scale(0.6)", offset: 0.15 },
      { opacity: 0, transform: "scale(2.4)" },
    ],
    { duration: 620, delay: 360, easing: EASE_OUT },
  );
  return new Promise((done) => setTimeout(done, 340));
}

/** Rolls the number in `holder` to `text`: up when the count rises, down when it falls. */
export function rollTo(holder, text, rising) {
  const current = holder.querySelector(".digit:not(.leaving)");
  if (current?.textContent === text) return;
  const next = document.createElement("span");
  next.className = "digit";
  next.textContent = text;
  if (!current || calm()) {
    holder.replaceChildren(next);
    return;
  }
  holder.querySelectorAll(".leaving").forEach((el) => el.remove());
  current.classList.add("leaving");
  holder.append(next);
  const from = rising ? "100%" : "-100%";
  const to = rising ? "-100%" : "100%";
  current.animate([{ transform: "translateY(0)", opacity: 1 }, { transform: `translateY(${to})`, opacity: 0 }], {
    duration: 220,
    easing: EASE_OUT,
  }).finished.then(() => current.remove());
  next.animate([{ transform: `translateY(${from})`, opacity: 0 }, { transform: "translateY(0)", opacity: 1 }], {
    duration: 260,
    easing: EASE_OUT,
  });
}

/** Moves the room underline under `tab`; the first placement does not slide. */
export function placeLine(line, tab) {
  if (!tab) return;
  line.style.setProperty("--x", `${tab.offsetLeft}px`);
  line.style.setProperty("--w", String(tab.offsetWidth / 100));
  if (!line.classList.contains("is-live")) requestAnimationFrame(() => requestAnimationFrame(() => line.classList.add("is-live")));
}
