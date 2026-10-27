// Settings: the look (follow the device, light, or dark), how long a day in the tank lasts, and sound.
const $ = (id) => document.getElementById(id);

export function createSettings({ getState, onLook, onCycle, onSound, onOpen, onClose, tankNote }) {
  const panel = $("settings");
  const scrim = $("scrim");
  const button = $("settingsBtn");
  const look = $("lookSeg");
  const cycle = $("cycleSel");
  const sound = $("soundSw");
  let open = false;

  function fill() {
    const s = getState();
    for (const b of look.querySelectorAll(".seg-btn")) b.setAttribute("aria-checked", String(b.dataset.look === s.look));
    const value = String(s.cycleMinutes);
    if (![...cycle.options].some((o) => o.value === value)) {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = `${value} minutes`;
      cycle.append(o);
    }
    cycle.value = value;
    sound.setAttribute("aria-checked", String(!!s.sound));
    $("tankNote").textContent = tankNote();
  }

  function show() {
    if (open) return;
    open = true;
    fill();
    panel.classList.add("is-open");
    scrim.classList.add("is-open");
    panel.removeAttribute("inert");
    panel.setAttribute("aria-hidden", "false");
    button.setAttribute("aria-expanded", "true");
    onOpen();
    setTimeout(() => look.querySelector("[aria-checked='true']")?.focus({ preventScroll: true }), 60);
  }

  function hide() {
    if (!open) return;
    open = false;
    panel.classList.remove("is-open");
    scrim.classList.remove("is-open");
    panel.setAttribute("inert", "");
    panel.setAttribute("aria-hidden", "true");
    button.setAttribute("aria-expanded", "false");
    onClose();
  }

  look.addEventListener("click", (ev) => {
    const b = ev.target.closest(".seg-btn");
    if (!b) return;
    onLook(b.dataset.look);
    fill();
  });
  cycle.addEventListener("change", () => onCycle(Number(cycle.value)));
  sound.addEventListener("click", () => {
    onSound(sound.getAttribute("aria-checked") !== "true");
    fill();
  });
  button.addEventListener("click", () => (open ? hide() : show()));
  $("settingsClose").addEventListener("click", hide);
  scrim.addEventListener("click", hide);

  return { show, hide, isOpen: () => open };
}
