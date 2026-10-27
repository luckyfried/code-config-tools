// The card for the 2048 moment and for a board with no moves left. It sits clear of the tray: under it on a wide
// screen, over the game buttons on a phone, in the side column of a phone on its side.
export function createMoment(root) {
  const el = root.querySelector("[data-moment]");
  const kicker = el.querySelector("[data-moment-kicker]");
  const title = el.querySelector("[data-moment-title]");
  const line = el.querySelector("[data-moment-line]");
  const first = el.querySelector("[data-moment-first]");
  const second = el.querySelector("[data-moment-second]");
  let handlers = {};
  first.addEventListener("click", () => handlers.first?.());
  second.addEventListener("click", () => handlers.second?.());
  let leaving = 0;
  return {
    get open() {
      return !el.hidden && !el.classList.contains("is-leaving");
    },
    show(content) {
      clearTimeout(leaving);
      el.classList.remove("is-leaving");
      kicker.textContent = content.kicker;
      title.textContent = content.title;
      line.textContent = content.line;
      first.textContent = content.first.label;
      handlers = { first: content.first.onClick, second: content.second?.onClick };
      second.hidden = !content.second;
      if (content.second) second.textContent = content.second.label;
      el.hidden = false;
      root.classList.add("has-moment");
      if (content.focus !== false) requestAnimationFrame(() => first.focus({ preventScroll: true }));
    },
    hide() {
      if (el.hidden) return;
      el.classList.add("is-leaving");
      root.classList.remove("has-moment");
      leaving = setTimeout(() => {
        el.hidden = true;
        el.classList.remove("is-leaving");
      }, 140);
    },
  };
}
