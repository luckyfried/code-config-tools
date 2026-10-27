// The settings sheet: board size, look, day or night, sound, and resetting the best score for this size.
// The look cards preview each theme's own ramp, read from its theme file.

function block(css, selector) {
  const at = css.indexOf(selector);
  if (at < 0) return "";
  const open = css.indexOf("{", at);
  return css.slice(open + 1, css.indexOf("}", open));
}

function pick(text, name) {
  const m = new RegExp(`${name}:\\s*([^;]+);`).exec(text);
  return m ? m[1].trim() : "";
}

export function createSettings(root, { get, onSize, onTheme, onAppearance, onSound, onResetBest, onOpen, onClose }) {
  const dialog = root.querySelector("[data-settings]");
  const form = dialog.querySelector("form");
  const sound = dialog.querySelector("[data-sound]");
  const reset = dialog.querySelector("[data-reset]");
  const confirm = dialog.querySelector("[data-reset-confirm]");
  const question = dialog.querySelector("[data-reset-question]");
  const ramps = new Map();

  async function preview(dark) {
    for (const el of dialog.querySelectorAll("[data-ramp]")) {
      const name = el.dataset.ramp;
      if (!ramps.has(name)) {
        try {
          const res = await fetch(`./themes/${name}.css`);
          ramps.set(name, await res.text());
        } catch {
          ramps.set(name, "");
        }
      }
      const css = ramps.get(name);
      const vars = dark ? block(css, '[data-theme="dark"]') : block(css, '[data-theme="light"]');
      el.style.setProperty("--swatch-tray", pick(vars, "--scene-tray") || "transparent");
      const swatches = el.querySelectorAll("i");
      ["--cube-1", "--cube-5", "--cube-8", "--cube-11"].forEach((token, i) => swatches[i]?.style.setProperty("--swatch", pick(vars, token)));
    }
  }

  function fill() {
    const s = get();
    form.elements.size.value = String(s.size);
    form.elements.theme.value = s.theme;
    form.elements.appearance.value = s.appearance;
    sound.checked = s.sound;
    confirm.hidden = true;
    reset.hidden = false;
    reset.disabled = s.best === 0;
    question.textContent = `Reset the best for ${s.size} × ${s.size}?`;
    preview(s.dark);
  }

  form.addEventListener("change", (event) => {
    const t = event.target;
    if (t.name === "size") onSize(Number(t.value));
    else if (t.name === "theme") onTheme(t.value);
    else if (t.name === "appearance") onAppearance(t.value);
    else if (t === sound) onSound(sound.checked);
    fill();
  });
  reset.addEventListener("click", () => {
    reset.hidden = true;
    confirm.hidden = false;
  });
  dialog.querySelector("[data-reset-no]").addEventListener("click", () => fill());
  dialog.querySelector("[data-reset-yes]").addEventListener("click", () => {
    onResetBest();
    fill();
  });
  dialog.addEventListener("close", () => onClose());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  return {
    get open() {
      return dialog.open;
    },
    show() {
      fill();
      onOpen();
      dialog.showModal();
    },
    refresh() {
      if (dialog.open) fill();
    },
  };
}
