// Flip tiles counting down to the start: each digit that changes folds its top half down over the new number.
const pad = (n, size) => String(n).padStart(size, "0");

function setTile(tile, value, animate) {
  const top = tile.querySelector(".flip__half--top .flip__num");
  const bottom = tile.querySelector(".flip__half--bottom .flip__num");
  const from = top.textContent;
  if (from === value) return;
  if (!animate) {
    top.textContent = value;
    bottom.textContent = value;
    return;
  }
  const leafTop = document.createElement("span");
  leafTop.className = "flip__leaf flip__leaf--top";
  leafTop.innerHTML = `<span class="flip__num">${from}</span>`;
  const leafBottom = document.createElement("span");
  leafBottom.className = "flip__leaf flip__leaf--bottom";
  leafBottom.innerHTML = `<span class="flip__num">${value}</span>`;
  top.textContent = value;
  tile.append(leafTop, leafBottom);
  leafTop.animate([{ transform: "rotateX(0deg)" }, { transform: "rotateX(-90deg)" }],
    { duration: 260, easing: "cubic-bezier(0.55, 0, 1, 0.45)", fill: "forwards" });
  const fall = leafBottom.animate([{ transform: "rotateX(90deg)" }, { transform: "rotateX(0deg)" }],
    { duration: 300, delay: 260, easing: "cubic-bezier(0.34, 1.4, 0.64, 1)", fill: "both" });
  fall.onfinish = () => {
    bottom.textContent = value;
    leafTop.remove();
    leafBottom.remove();
  };
}

export function startCountdown(root, target, { animate }) {
  const units = {};
  for (const unit of root.querySelectorAll("[data-unit]")) units[unit.dataset.unit] = [...unit.querySelectorAll(".flip")];
  let first = true;
  const tick = () => {
    const left = Math.max(0, target - Date.now());
    if (left === 0) {
      root.classList.add("is-past");
      return;
    }
    const s = Math.floor(left / 1000);
    const values = {
      days: Math.min(999, Math.floor(s / 86400)),
      hours: Math.floor(s / 3600) % 24,
      minutes: Math.floor(s / 60) % 60,
      seconds: s % 60,
    };
    for (const [unit, tiles] of Object.entries(units)) {
      const size = unit === "days" ? Math.max(2, String(values.days).length) : 2;
      const text = pad(values[unit], tiles.length);
      tiles.forEach((tile, i) => {
        tile.hidden = i < tiles.length - size;
        setTile(tile, text[i], animate && !first);
      });
    }
    first = false;
    setTimeout(tick, 1000 - (Date.now() % 1000) + 5);
  };
  tick();
}
