// The thin chrome around the sky: the place and the date (the one date on the page, which follows the ribbon), the
// Tonight panel, the time ribbon, the card for a tapped star, and the settings sheet. HTML styled by the tokens; the sky never waits on it.
import { formatTime, formatHour, formatDay, formatYear, dateInputValue, timeInputValue } from "./time.js";

const $ = (id) => document.getElementById(id);
const DAY = 86400e3;

const ICONS = {
  sunset: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 18h18"/><path d="M7 18a5 5 0 0 1 10 0"/><path d="M12 4v5M9.5 7.5 12 10l2.5-2.5"/></svg>',
  dark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l1.6 4.9 5.1.1-4.1 3.1 1.5 4.9-4.1-3-4.1 3 1.5-4.9-4.1-3.1 5.1-.1z"/></svg>',
  moonrise: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.5 4.5a7 7 0 1 0 4 12.3A6 6 0 0 1 15.5 4.5z"/></svg>',
  sunrise: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 18h18"/><path d="M7 18a5 5 0 0 1 10 0"/><path d="M12 10V5M9.5 6.5 12 4l2.5 2.5"/></svg>',
};

const PLANET_DOTS = {
  Mercury: "rgb(219, 204, 189)",
  Venus: "rgb(255, 246, 222)",
  Mars: "rgb(255, 150, 104)",
  Jupiter: "rgb(255, 228, 188)",
  Saturn: "rgb(246, 218, 156)",
  Uranus: "rgb(178, 234, 240)",
  Neptune: "rgb(148, 184, 255)",
};

export function createHud(handlers) {
  const els = {
    placeName: $("place-name"),
    whenText: $("when-text"),
    tonight: $("tonight"),
    tonightToggle: $("tonight-toggle"),
    events: $("tonight-events"),
    moonDisc: $("moon-disc"),
    moonPhase: $("moon-phase"),
    moonDetail: $("moon-detail"),
    planets: $("planets"),
    timeOut: $("time-out"),
    ribbon: $("ribbon"),
    band: $("ribbon-band"),
    moonBand: $("ribbon-moon"),
    ticks: $("ribbon-ticks"),
    thumb: $("ribbon-thumb"),
    spin: $("spin-btn"),
    now: $("now-btn"),
    card: $("star-card"),
    cardKind: $("star-kind"),
    cardName: $("star-name"),
    cardDesig: $("star-desig"),
    cardFacts: $("star-facts"),
    cardClose: $("star-close"),
    settings: $("settings"),
    settingsBtn: $("settings-btn"),
    sensorBtn: $("sensor-btn"),
    sensorHint: $("sensor-hint"),
  };
  let tz = "UTC";
  let windowStart = 0;
  let lastMinute = -1;
  let lastThumb = -1;
  let night = null;

  // Entrance: the chrome rises into place once, staggered, after the sky is already up.
  requestAnimationFrame(() => document.body.classList.add("is-ready"));

  // The phone stacks Tonight on the time bar; the bar's real height keeps a gap between them.
  const timebar = document.querySelector(".timebar");
  if (timebar && "ResizeObserver" in window) {
    new ResizeObserver(() => {
      document.documentElement.style.setProperty("--timebar-h", `${Math.ceil(timebar.offsetHeight)}px`);
    }).observe(timebar);
  }

  els.tonightToggle.addEventListener("click", () => {
    const open = els.tonight.classList.toggle("is-open");
    els.tonightToggle.setAttribute("aria-expanded", String(open));
  });

  els.spin.addEventListener("click", () => handlers.spin());
  els.now.addEventListener("click", () => handlers.now());
  els.cardClose.addEventListener("click", () => handlers.deselect());
  els.settingsBtn.addEventListener("click", () => {
    handlers.openSettings();
    els.settings.showModal();
  });
  els.settings.addEventListener("click", (e) => {
    if (e.target === els.settings) els.settings.close();
  });
  els.sensorBtn.addEventListener("click", () => handlers.sensor());

  // The ribbon: 24 hours from local noon; drag or use the arrow keys to move through the night.
  const ribbonTime = (clientX) => {
    const r = els.ribbon.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    return windowStart + f * DAY;
  };
  let ribbonDrag = false;
  els.ribbon.addEventListener("pointerdown", (e) => {
    els.ribbon.setPointerCapture(e.pointerId);
    ribbonDrag = true;
    els.ribbon.classList.add("is-dragging");
    handlers.scrubStart();
    handlers.scrub(ribbonTime(e.clientX));
  });
  els.ribbon.addEventListener("pointermove", (e) => {
    if (ribbonDrag) handlers.scrub(ribbonTime(e.clientX));
  });
  const ribbonEnd = () => {
    if (!ribbonDrag) return;
    ribbonDrag = false;
    els.ribbon.classList.remove("is-dragging");
    handlers.scrubEnd();
  };
  els.ribbon.addEventListener("pointerup", ribbonEnd);
  els.ribbon.addEventListener("pointercancel", ribbonEnd);
  els.ribbon.addEventListener("keydown", (e) => {
    const step = (e.shiftKey ? 60 : 10) * 60e3;
    const map = { ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step, PageUp: 3600e3, PageDown: -3600e3 };
    if (e.key in map) {
      e.preventDefault();
      handlers.step(map[e.key]);
    } else if (e.key === "Home" && night && night.sunset) {
      e.preventDefault();
      handlers.glide(night.sunset.getTime());
    } else if (e.key === "End" && night && night.sunrise) {
      e.preventDefault();
      handlers.glide(night.sunrise.getTime());
    }
  });

  // Settings: every control applies at once.
  const form = $("settings-form");
  form.addEventListener("change", (e) => {
    const t = e.target;
    if (t.type === "radio") handlers.setting(t.name, t.value);
    else if (t.id === "set-date" || t.id === "set-time") handlers.dateTime($("set-date").value, $("set-time").value);
    else if (t.id === "set-lat" || t.id === "set-lon" || t.id === "set-place") {
      handlers.place($("set-place").value, parseFloat($("set-lat").value), parseFloat($("set-lon").value));
    }
  });

  function fillSettings(state) {
    for (const name of ["labels", "constellations", "horizon", "theme"]) {
      const input = form.querySelector(`input[name="${name}"][value="${state.settings[name]}"]`);
      if (input) input.checked = true;
    }
    $("set-place").value = state.place.name;
    $("set-lat").value = state.place.lat.toFixed(4);
    $("set-lon").value = state.place.lon.toFixed(4);
    $("set-date").value = dateInputValue(state.ms, tz);
    $("set-time").value = timeInputValue(state.ms, tz);
  }

  function setPlace(place) {
    tz = place.timezone;
    els.placeName.textContent = place.name;
    document.title = `${place.name}: Sky Tonight`;
    lastMinute = -1;
  }

  let lastText = 0;
  const texts = { time: "", when: "" };
  const put = (key, el, value) => {
    if (texts[key] !== value) {
      texts[key] = value;
      el.textContent = value;
    }
  };
  function setTime(ms, spinning) {
    const minute = Math.floor(ms / 60e3);
    const nowReal = performance.now();
    // While time runs fast the readout ticks about six times a second; at rest it follows every minute.
    if (minute !== lastMinute && (!spinning || nowReal - lastText > 160)) {
      lastMinute = minute;
      lastText = nowReal;
      const t = formatTime(ms, tz);
      put("time", els.timeOut, t);
      const day = formatDay(ms, tz);
      put("when", els.whenText, `${day}, ${formatYear(ms, tz)}`);
      if (!spinning) {
        els.ribbon.setAttribute("aria-valuenow", String(Math.round((ms - windowStart) / 60e3)));
        els.ribbon.setAttribute("aria-valuetext", `${t}, ${day}`);
      }
    }
    const f = Math.max(0, Math.min(1, (ms - windowStart) / DAY));
    if (Math.abs(f - lastThumb) > 0.0002) {
      lastThumb = f;
      els.thumb.style.setProperty("--pos", f.toFixed(5));
    }
    els.spin.setAttribute("aria-pressed", String(!!spinning));
    els.spin.classList.toggle("is-on", !!spinning);
  }

  function eventButton(kind, label, date) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = `event event--${kind}`;
    b.innerHTML = `<span class="event__icon">${ICONS[kind]}</span><span class="event__label"></span><time class="event__time"></time>`;
    b.querySelector(".event__label").textContent = label;
    const time = b.querySelector(".event__time");
    time.textContent = formatTime(date.getTime(), tz);
    time.dateTime = date.toISOString();
    b.addEventListener("click", () => handlers.glide(date.getTime()));
    li.appendChild(b);
    return li;
  }

  function setNight(n, bands) {
    night = n;
    windowStart = n.start;
    lastThumb = -1;
    els.events.replaceChildren();
    const list = [];
    if (n.sunset) list.push(["sunset", "Sunset", n.sunset]);
    if (n.dark) list.push(["dark", "Full dark", n.dark]);
    else if (n.nauticalDark) list.push(["dark", "Deep twilight", n.nauticalDark]);
    const moonEvents = [];
    if (n.moonrise) moonEvents.push(["moonrise", "Moonrise", n.moonrise]);
    if (n.moonset) moonEvents.push(["moonrise", "Moonset", n.moonset]);
    moonEvents.sort((a, b) => a[2] - b[2]);
    list.push(...moonEvents.slice(0, 1));
    if (n.sunrise) list.push(["sunrise", "Sunrise", n.sunrise]);
    list.sort((a, b) => a[2] - b[2]);
    list.forEach(([kind, label, date], i) => {
      const li = eventButton(kind, label, date);
      li.style.setProperty("--i", String(i));
      els.events.appendChild(li);
    });
    els.ribbon.style.setProperty("--band", bands.grad);
    els.ribbon.style.setProperty("--moon-band", bands.moon);
    els.ticks.replaceChildren();
    for (let h = 3; h <= 21; h += 3) {
      const t = windowStart + h * 3600e3;
      const tick = document.createElement("span");
      tick.className = h % 6 === 0 ? "tick tick--major" : "tick";
      tick.style.setProperty("--at", String(h / 24));
      tick.textContent = formatHour(t, tz);
      els.ticks.appendChild(tick);
    }
  }

  function drawMoon(canvas, angle, colors) {
    const g = canvas.getContext("2d");
    const s = canvas.width;
    const r = s * 0.42;
    g.clearRect(0, 0, s, s);
    g.save();
    g.translate(s / 2, s / 2);
    g.fillStyle = colors.dark;
    g.beginPath();
    g.arc(0, 0, r, 0, Math.PI * 2);
    g.fill();
    const phase = (angle % 360) / 360;
    const waxing = phase < 0.5;
    const k = Math.cos(phase * 2 * Math.PI);
    g.fillStyle = colors.lit;
    g.beginPath();
    g.arc(0, 0, r, -Math.PI / 2, Math.PI / 2, !waxing);
    g.ellipse(0, 0, Math.abs(k) * r, r, 0, Math.PI / 2, -Math.PI / 2, (k > 0) === waxing ? true : false);
    g.fill();
    g.restore();
  }

  function setMoon(info, events, colors) {
    els.moonPhase.textContent = info.name;
    let detail = `${info.lit}% lit`;
    if (info.altitude > 0 && events.moonset) detail += `, sets ${formatTime(events.moonset.getTime(), tz)}`;
    else if (events.moonrise) detail += `, rises ${formatTime(events.moonrise.getTime(), tz)}`;
    else if (info.altitude > 0) detail += ", up all night";
    els.moonDetail.textContent = detail;
    drawMoon(els.moonDisc, info.angle, colors);
  }

  function setPlanets(list, ms, mono) {
    els.planets.replaceChildren();
    if (list.length === 0) {
      const li = document.createElement("li");
      li.className = "planets__none";
      li.textContent = `None above the horizon at ${formatTime(ms, tz)}.`;
      els.planets.appendChild(li);
      return;
    }
    for (const p of list) {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "planet";
      b.innerHTML = '<span class="planet__dot"></span><span class="planet__name"></span><span class="planet__where"></span>';
      b.querySelector(".planet__dot").style.setProperty("--dot", mono ? "var(--color-accent)" : PLANET_DOTS[p.name]);
      b.querySelector(".planet__name").textContent = p.name;
      b.querySelector(".planet__where").textContent = `${p.where}, ${Math.round(p.alt)}°`;
      b.setAttribute("aria-label", `${p.name}, ${Math.round(p.alt)} degrees up in the ${p.where}. Turn to it.`);
      b.addEventListener("click", () => handlers.lookAt(p.name));
      li.appendChild(b);
      els.planets.appendChild(li);
    }
  }

  function showCard(info, anchor) {
    els.cardKind.textContent = info.kind;
    els.cardName.textContent = info.name;
    els.cardDesig.textContent = info.desig || "";
    els.cardDesig.hidden = !info.desig;
    els.cardFacts.replaceChildren();
    for (const [k, v] of info.facts) {
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v;
      els.cardFacts.append(dt, dd);
    }
    els.card.hidden = false;
    if (anchor) {
      els.card.style.setProperty("--ax", `${Math.round(anchor.x)}px`);
      els.card.style.setProperty("--ay", `${Math.round(anchor.y)}px`);
    }
    els.card.classList.remove("is-on");
    void els.card.offsetWidth;
    els.card.classList.add("is-on");
    document.body.classList.add("has-card");
  }

  function hideCard() {
    els.card.classList.remove("is-on");
    document.body.classList.remove("has-card");
    setTimeout(() => {
      if (!els.card.classList.contains("is-on")) els.card.hidden = true;
    }, 220);
  }

  function setSensor(on, supported) {
    els.sensorBtn.setAttribute("aria-pressed", String(on));
    els.sensorBtn.classList.toggle("is-on", on);
    els.sensorBtn.hidden = !supported;
    els.sensorHint.hidden = !on;
    if (on) {
      els.sensorHint.classList.add("is-on");
      setTimeout(() => els.sensorHint.classList.remove("is-on"), 4500);
    }
  }

  return { els, setPlace, setTime, setNight, setMoon, setPlanets, showCard, hideCard, fillSettings, setSensor, get tz() { return tz; } };
}
