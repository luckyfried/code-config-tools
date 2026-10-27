// One pointerdown handler for both halves of the screen, so two thumbs are timed by the same clock
// (event.timeStamp); A and L do the same on a keyboard, Space starts and continues, Escape goes back to the title.

export function createInput({ stage, onShot, onGo, onBack, onAny }) {
  const fromInput = (event) => {
    const t = event.target;
    return t instanceof HTMLElement && (t.isContentEditable || t.tagName === "INPUT" || t.tagName === "TEXTAREA");
  };

  stage.addEventListener(
    "pointerdown",
    (event) => {
      if (!event.isPrimary && event.pointerType === "mouse") return;
      const rect = stage.getBoundingClientRect();
      const side = event.clientX - rect.left < rect.width / 2 ? 0 : 1;
      onShot(side, event.timeStamp, event.pointerType);
      onAny?.();
      event.preventDefault();
    },
    { passive: false },
  );
  // a long press on a phone must never open a menu under a thumb
  stage.addEventListener("contextmenu", (event) => event.preventDefault());

  window.addEventListener("keydown", (event) => {
    if (fromInput(event)) {
      if (event.key === "Enter") onGo?.(event);
      return;
    }
    onAny?.();
    if (event.repeat) return;
    const key = event.key.toLowerCase();
    if (key === "a") onShot(0, event.timeStamp, "key");
    else if (key === "l") onShot(1, event.timeStamp, "key");
    else if (event.code === "Space" || key === "enter") {
      // a focused button answers Space and Enter itself
      if (event.target instanceof HTMLButtonElement) return;
      event.preventDefault();
      onGo?.(event);
    } else if (key === "escape") onBack?.();
  });

  window.addEventListener("pointerdown", () => onAny?.(), { passive: true });
}
