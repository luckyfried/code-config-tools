// The heads-up display: the crystal count and pips, the compass to the nearest crystal, the clock, the toast, and
// the hint. Text changes only when its value changes.

const $ = (id) => document.getElementById(id);

export function clockText(seconds) {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function createHud(total) {
  const found = $("found-count");
  const pips = $("pips");
  const compass = $("compass");
  const needle = $("compass-needle");
  const clock = $("clock");
  const clockTime = $("clock-time");
  const toast = $("toast");
  const hint = $("hint");
  $("total-count").textContent = String(total);
  pips.replaceChildren(
    ...Array.from({ length: total }, () => {
      const pip = document.createElement("span");
      pip.className = "pip";
      return pip;
    }),
  );

  let lastClock = "";
  let lastAngle = NaN;
  let toastTimer = 0;
  let hintTimer = 0;

  return {
    reset() {
      found.textContent = "0";
      for (const pip of pips.children) pip.classList.remove("is-found");
      compass.classList.remove("is-done");
      clock.classList.remove("is-late");
      toast.classList.remove("is-on");
      hint.classList.remove("is-on");
      lastClock = "";
    },
    setFound(count) {
      found.textContent = String(count);
      [...pips.children].forEach((pip, i) => pip.classList.toggle("is-found", i < count));
      compass.classList.toggle("is-done", count >= total);
    },
    setClock(remaining, late) {
      const text = clockText(remaining);
      if (text !== lastClock) {
        clockTime.textContent = text;
        lastClock = text;
      }
      clock.classList.toggle("is-late", late);
    },
    setCompass(degrees) {
      const rounded = Math.round(degrees);
      if (rounded !== lastAngle) {
        needle.style.setProperty("--compass-angle", `${rounded}deg`);
        lastAngle = rounded;
      }
    },
    toast(text, seconds = 1.6) {
      toast.textContent = text;
      toast.classList.add("is-on");
      toastTimer = seconds;
    },
    hint(text, seconds = 4.5) {
      hint.textContent = text;
      hint.classList.add("is-on");
      hintTimer = seconds;
    },
    update(dt) {
      if (toastTimer > 0 && (toastTimer -= dt) <= 0) toast.classList.remove("is-on");
      if (hintTimer > 0 && (hintTimer -= dt) <= 0) hint.classList.remove("is-on");
    },
  };
}
