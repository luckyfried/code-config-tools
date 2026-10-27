// The HUD and the screens over the scene, as DOM. Values are written only when they change.
const $ = (id) => document.getElementById(id);
const number = new Intl.NumberFormat("en-US");

export function createHud() {
  const el = {
    clock: $("clock"), clockTime: $("clockTime"), clockBar: $("clockBar"),
    objective: $("objective"), objIcon: $("objIcon"), objKind: $("objKind"), objName: $("objName"), objDist: $("objDist"), objArrow: $("objArrow"),
    live: $("live"), liveIcon: $("liveIcon"), liveKind: $("liveKind"), liveName: $("liveName"), liveDist: $("liveDist"),
    delivered: $("delivered"), bonus: $("bonus"), toasts: $("toasts"), keysHint: $("keysHint"),
    title: $("title"), dispatchSub: $("dispatchSub"), pilotName: $("pilotName"), shiftLength: $("shiftLength"), bestShift: $("bestShift"),
    over: $("over"), overPilot: $("overPilot"), overScore: $("overScore"), overDelivered: $("overDelivered"), overBonus: $("overBonus"),
    overBest: $("overBest"), overNewBest: $("overNewBest"), pause: $("pause"), soundButton: $("soundButton"),
  };
  const last = {};
  const set = (key, node, text) => {
    if (last[key] !== text) {
      last[key] = text;
      node.textContent = text;
    }
  };

  return {
    el,
    setMode(mode) {
      const body = document.body;
      body.classList.toggle("is-dispatch", mode === "dispatch");
      body.classList.toggle("is-shift", mode === "shift" || mode === "pause");
      body.classList.toggle("is-over", mode === "over");
      el.over.hidden = mode !== "over";
      el.pause.hidden = mode !== "pause";
    },
    setDispatch({ title, cityName, pilotName, shiftSeconds, best, light }) {
      set("title", el.title, title);
      set("sub", el.dispatchSub, `${light ? "Dusk" : "Night"} shift over ${cityName}`);
      set("pilot", el.pilotName, pilotName);
      set("shift", el.shiftLength, `${shiftSeconds} s`);
      set("best", el.bestShift, best ? `${number.format(best.score)} pts` : "None yet");
    },
    setObjective(task, distance, bearing, attract) {
      const kind = task.kind === "pickup" ? "Pick up" : "Drop off";
      const icon = task.kind === "pickup" ? "#i-package" : "#i-balcony";
      const dist = distance >= 1000 ? `${(distance / 1000).toFixed(1)} km` : `${Math.max(0, Math.round(distance))} m`;
      if (last.icon !== icon) {
        last.icon = icon;
        el.objIcon.setAttribute("href", icon);
        el.liveIcon.setAttribute("href", icon);
        el.objective.classList.toggle("is-drop", task.kind !== "pickup");
        el.live.classList.toggle("is-drop", task.kind !== "pickup");
      }
      if (attract) {
        set("liveKind", el.liveKind, `On the route now: ${kind.toLowerCase()}`);
        set("liveName", el.liveName, task.name);
        set("liveDist", el.liveDist, dist);
      } else {
        set("objKind", el.objKind, kind);
        set("objName", el.objName, task.name);
        set("objDist", el.objDist, dist);
        const deg = Math.round(bearing);
        if (last.bearing !== deg) {
          last.bearing = deg;
          el.objArrow.style.setProperty("--bearing", `${deg}deg`);
        }
      }
    },
    setClock(left, total) {
      const s = Math.max(0, left);
      const text = s < 10 ? s.toFixed(1) : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
      set("clock", el.clockTime, text);
      const low = s < 10;
      if (last.low !== low) {
        last.low = low;
        el.clock.classList.toggle("is-low", low);
      }
      const frac = Math.min(1, s / Math.max(total, 1)).toFixed(3);
      if (last.frac !== frac) {
        last.frac = frac;
        el.clockBar.style.setProperty("--left", frac);
      }
    },
    setTally(delivered, bonus) {
      set("delivered", el.delivered, String(delivered));
      set("bonus", el.bonus, number.format(bonus));
    },
    toast(value, label, kind = "") {
      const node = document.createElement("div");
      node.className = `toast ${kind ? `is-${kind}` : ""}`;
      const v = document.createElement("span");
      v.className = "toast-value";
      v.textContent = value;
      const l = document.createElement("span");
      l.className = "toast-label";
      l.textContent = label;
      node.append(v, l);
      el.toasts.prepend(node);
      while (el.toasts.children.length > 3) el.toasts.lastChild.remove();
      setTimeout(() => {
        node.classList.add("is-leaving");
        setTimeout(() => node.remove(), 260);
      }, 1500);
    },
    hideKeysHint() {
      el.keysHint.classList.add("is-done");
    },
    showKeysHint() {
      el.keysHint.classList.remove("is-done");
    },
    showOver({ pilotName, score, delivered, bonus, best, newBest }) {
      el.overPilot.textContent = `${pilotName}, your shift is done`;
      el.overScore.textContent = number.format(score);
      el.overDelivered.textContent = String(delivered);
      el.overBonus.textContent = number.format(bonus);
      el.overBest.textContent = number.format(best);
      el.overNewBest.hidden = !newBest;
    },
    setMuted(muted) {
      document.body.classList.toggle("is-muted", muted);
      el.soundButton.setAttribute("aria-label", muted ? "Turn sound on" : "Turn sound off");
      el.soundButton.setAttribute("aria-pressed", String(muted));
    },
  };
}
