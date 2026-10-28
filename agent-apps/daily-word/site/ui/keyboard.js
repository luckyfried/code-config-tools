// The on-screen keyboard: one pointer path for touch and mouse, and the same press feel for physical keys.

const ROWS = ["QWERTYUIOP", "ASDFGHJKL", "+ZXCVBNM-"];
const BACKSPACE =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8.6 5h10.4A2 2 0 0 1 21 7v10a2 2 0 0 1-2 2H8.6a2 2 0 0 1-1.5-.7L2.6 12l4.5-6.3A2 2 0 0 1 8.6 5z"/><path d="M11.5 9.5l5 5M16.5 9.5l-5 5"/></svg>';

export function createKeyboard(root, onKey, { reduced }) {
  const keys = new Map();
  ROWS.forEach((letters, r) => {
    const row = document.createElement("div");
    row.className = r === 1 ? "key-row is-middle" : "key-row";
    for (const ch of letters) {
      const key = document.createElement("button");
      key.type = "button";
      key.className = "key";
      const label = document.createElement("span");
      label.className = "key-label";
      if (ch === "+") {
        key.dataset.key = "Enter";
        key.classList.add("is-wide");
        label.textContent = "Enter";
      } else if (ch === "-") {
        key.dataset.key = "Backspace";
        key.classList.add("is-wide");
        key.setAttribute("aria-label", "Delete letter");
        label.innerHTML = BACKSPACE;
      } else {
        key.dataset.key = ch;
        label.textContent = ch;
      }
      key.appendChild(label);
      row.appendChild(key);
      keys.set(key.dataset.key, key);
    }
    root.appendChild(row);
  });

  // Pointer down types at once, so fast thumbs never wait for a click; the key keeps focus off itself.
  root.addEventListener("pointerdown", (event) => {
    const key = event.target.closest(".key");
    if (!key) return;
    event.preventDefault();
    press(key.dataset.key);
    onKey(key.dataset.key, "pointer");
  });
  const release = () => keys.forEach((k) => k.classList.remove("is-pressed"));
  root.addEventListener("pointerup", release);
  root.addEventListener("pointercancel", release);
  root.addEventListener("pointerleave", release);
  // A keyboard user who tabs to a key and presses Enter or Space still types it.
  root.addEventListener("click", (event) => {
    const key = event.target.closest(".key");
    if (key && event.detail === 0) onKey(key.dataset.key, "pointer");
  });

  /** The key dips and sends out a ring. */
  function press(name) {
    const key = keys.get(name);
    if (!key) return;
    key.classList.add("is-pressed");
    setTimeout(() => key.classList.remove("is-pressed"), 130);
    if (reduced.matches) return;
    const ring = key.animate(
      [
        { opacity: 0.95, transform: "scale(1)" },
        { opacity: 0, transform: "scale(1.22, 1.32)" },
      ],
      { duration: 380, easing: "cubic-bezier(0.23, 1, 0.32, 1)", pseudoElement: "::after" },
    );
    ring.finished.catch(() => {});
  }

  function setStates(states) {
    keys.forEach((key, name) => {
      if (states[name]) key.dataset.state = states[name];
      else delete key.dataset.state;
      const base = name === "Enter" ? "Enter" : name === "Backspace" ? "Delete letter" : name;
      key.setAttribute("aria-label", states[name] ? `${base}, ${states[name] === "correct" ? "in the right spot" : states[name] === "present" ? "in the word" : "not in the word"}` : base);
    });
  }

  return { press, setStates };
}
