// Short messages at the top of the board: they drop in, wait, and lift away.

export function createToasts(root) {
  function show(message, { ms = 1500, persist = false } = {}) {
    while (root.children.length >= 3) root.firstElementChild.remove();
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    root.appendChild(toast);
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("is-in")));
    if (!persist) setTimeout(() => dismiss(toast), ms);
    return toast;
  }

  function dismiss(toast) {
    if (!toast.isConnected) return;
    toast.classList.add("is-out");
    setTimeout(() => toast.remove(), 170);
  }

  function clear() {
    [...root.children].forEach((t) => t.remove());
  }

  return { show, dismiss, clear };
}
