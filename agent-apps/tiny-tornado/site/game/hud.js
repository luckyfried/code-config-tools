// The rampage HUD. Text changes only when its value does; bars and rings move through custom properties.
import { massText } from "./scoring.js";

export function clockText(seconds) {
  const s = Math.ceil(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function createHud() {
  const $ = (id) => document.getElementById(id);
  const mass = $("mass");
  const time = $("time");
  const timeBlock = time.closest(".hud-time");
  const levelLabel = $("level-label");
  const pips = [...$("pips").children];
  const fill = $("level-fill");
  const toast = $("toast");
  const hint = $("hint");
  const pulseButton = $("pulse-button");
  const flash = $("flash");
  const last = { mass: "", time: "", level: 0, fill: -1, ready: -1, flash: -1 };

  return {
    reset(hintText) {
      hint.textContent = hintText;
      hint.classList.remove("is-gone");
      toast.classList.remove("is-on");
      last.mass = "";
      last.time = "";
      last.level = 0;
    },
    update({ mass: m, level, fill: f, timeLeft, ready }) {
      const mt = massText(m);
      if (mt !== last.mass) mass.textContent = last.mass = mt;
      const tt = clockText(timeLeft);
      if (tt !== last.time) {
        time.textContent = last.time = tt;
        timeBlock.classList.toggle("is-low", timeLeft <= 10);
      }
      if (level !== last.level) {
        last.level = level;
        levelLabel.textContent = `Funnel level ${level}`;
        pips.forEach((p, i) => p.classList.toggle("is-on", i < level));
      }
      const fr = Math.round(Math.min(1, Math.max(0, f)) * 100) / 100;
      if (fr !== last.fill) fill.style.setProperty("--fill", String((last.fill = fr)));
      const r = Math.round(Math.min(1, ready) * 20) / 20;
      if (r !== last.ready) {
        last.ready = r;
        pulseButton.style.setProperty("--ready", String(r));
        pulseButton.classList.toggle("is-cooling", r < 1);
      }
    },
    flash(value) {
      const v = Math.round(value * 20) / 20;
      if (v !== last.flash) flash.style.setProperty("--flash", String((last.flash = v)));
    },
    toast(text) {
      toast.textContent = text;
      toast.classList.add("is-on");
    },
    hideToast() {
      toast.classList.remove("is-on");
    },
    hideHint() {
      hint.classList.add("is-gone");
    },
  };
}
