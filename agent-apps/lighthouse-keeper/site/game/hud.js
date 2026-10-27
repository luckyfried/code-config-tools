// The HUD and the screens: text set once from the inputs, numbers written only when they change.
import { clock, count } from "./scoring.js";

const $ = (id) => document.getElementById(id);
const BOAT = '<svg viewBox="0 0 26 16" aria-hidden="true"><path d="M2 9h22l-4 5H6z"/><path d="M12 9V1l7 7z"/></svg>';

export function createHud(config, save, coarse) {
  const body = document.body;
  const hud = $("hud");
  const shore = $("shore");
  const turnedEl = $("turned");
  const dawnLeft = $("dawn-left");
  const flareBtn = $("flare-btn");
  const flareLabel = $("flare-label");
  const notice = $("notice");
  const hint = $("hud-hint");
  const last = { turned: -1, lost: -1, left: -1, dawn: -1, charge: -1, ready: null };
  let noticeTimer = 0;

  $("title-line").textContent = config.title;
  $("light-name").textContent = config.lighthouseName;
  $("hud-name").textContent = config.lighthouseName;
  $("result-kicker").textContent = `${config.lighthouseName}, kept by ${config.playerName}`;
  $("pause-kicker").textContent = config.lighthouseName;
  document.title = `${config.lighthouseName} · ${config.title}`;
  const minutes = config.nightMinutes === 1 ? "1 minute" : `${config.nightMinutes} minutes`;
  const lose = config.shipsToLose === 1 ? "One ship on the rocks" : `${cap(count(config.shipsToLose))} ships on the rocks`;
  $("terms").textContent = `Dawn comes in ${minutes}. ${lose} and the night is lost.`;
  $("hint").textContent = coarse
    ? "Drag anywhere to swing the beam. Tap the lamp to fire a flare."
    : "Move the mouse or hold Left and Right to swing the beam. Space fires a flare.";
  hint.textContent = coarse ? "Tap the lamp for a flare." : "Space fires a flare. Esc pauses.";
  shore.innerHTML = BOAT.repeat(config.shipsToLose);
  showBest(save);

  function showBest(s) {
    const best = $("best");
    if (s.bestTurned > 0) {
      best.hidden = false;
      best.textContent = `Best night: ${s.bestTurned} ${s.bestTurned === 1 ? "ship" : "ships"} turned back`;
    } else {
      best.hidden = true;
    }
  }

  return {
    showBest,
    mode(mode) {
      body.dataset.mode = mode;
    },
    reset() {
      last.turned = last.lost = last.left = last.dawn = last.charge = -1;
      last.ready = null;
      hint.classList.remove("is-gone");
    },
    update(night, charge, nightSeconds) {
      if (night.turned !== last.turned) {
        last.turned = night.turned;
        turnedEl.textContent = String(night.turned);
      }
      if (night.lost !== last.lost) {
        last.lost = night.lost;
        shore.querySelectorAll("svg").forEach((svg, i) => svg.classList.toggle("is-lost", i < night.lost));
        shore.setAttribute("aria-label", night.lost === 0 ? "No ships ashore" : `${night.lost} of ${config.shipsToLose} ships ashore`);
      }
      const left = Math.ceil(Math.max(0, nightSeconds - night.seconds));
      if (left !== last.left) {
        last.left = left;
        dawnLeft.textContent = `Dawn in ${clock(left)}`;
      }
      const dawn = Math.round((night.seconds / nightSeconds) * 200) / 200;
      if (dawn !== last.dawn) {
        last.dawn = dawn;
        hud.style.setProperty("--dawn", String(Math.min(1, dawn)));
      }
      const c = Math.round(charge * 100) / 100;
      if (c !== last.charge) {
        last.charge = c;
        flareBtn.style.setProperty("--charge", String(c));
      }
      const ready = charge >= 1;
      if (ready !== last.ready) {
        last.ready = ready;
        flareBtn.classList.toggle("is-ready", ready);
        flareLabel.textContent = ready ? "Flare" : `${Math.ceil((1 - charge) * 20)}s`;
        flareBtn.setAttribute("aria-label", ready ? "Fire a flare" : "The flare is charging");
      }
      if (!ready) {
        const s = `${Math.ceil((1 - charge) * 20)}s`;
        if (flareLabel.textContent !== s) flareLabel.textContent = s;
      }
      if (night.seconds > 9 && !hint.classList.contains("is-gone")) hint.classList.add("is-gone");
    },
    notice(text) {
      notice.textContent = text;
      notice.classList.add("is-shown");
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => notice.classList.remove("is-shown"), 2400);
    },
    showCard(id, on) {
      const el = $(id);
      el.classList.toggle("is-shown", on);
      if (on) {
        const primary = el.querySelector(".primary");
        if (primary) setTimeout(() => primary.focus({ preventScroll: true }), 60);
      }
    },
    result(dawn, night, save, newBest) {
      $("result-title").textContent = dawn ? "Dawn breaks" : "The night is lost";
      const n = night.turned;
      const ships = `${n} ${n === 1 ? "ship" : "ships"}`;
      $("result-line").textContent = dawn
        ? `${config.playerName}, you turned back ${ships} and kept the light until morning.${newBest ? " Your best night yet." : ""}`
        : `${cap(count(config.shipsToLose))} ${config.shipsToLose === 1 ? "ship" : "ships"} reached the rocks after ${clock(night.seconds)}. You turned back ${ships}.${newBest ? " Your best night yet." : ""}`;
      $("r-turned").textContent = String(n);
      $("r-time").textContent = clock(night.seconds);
      $("r-best").textContent = String(save.bestTurned);
    },
  };
}

function cap(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
