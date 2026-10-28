// The sheets: native dialogs, so focus stays inside and Escape closes; they slide in and out from CSS.

export function createSheets({ onClose = () => {} } = {}) {
  const open = (id) => {
    const dialog = document.getElementById(id);
    if (!dialog || dialog.open) return;
    document.querySelectorAll("dialog[open]").forEach((d) => d.close());
    dialog.showModal();
    const body = dialog.querySelector(".sheet-body");
    if (body) body.scrollTop = 0;
  };

  const close = (dialog) => {
    if (dialog?.open) dialog.close();
  };

  document.querySelectorAll("dialog.sheet").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close(dialog);
      if (event.target.closest("[data-close]")) close(dialog);
    });
    dialog.addEventListener("close", () => onClose(dialog.id));
  });

  document.querySelectorAll("[data-open]").forEach((button) => {
    button.addEventListener("click", () => open(button.dataset.open));
  });

  const anyOpen = () => !!document.querySelector("dialog[open]");

  return { open, close: (id) => close(document.getElementById(id)), anyOpen };
}
