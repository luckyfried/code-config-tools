// The HTML around the water: the surface sheet's species grid, the dive HUD, the results roll, and the photo viewer.
// It reads game state and writes classes, text, and custom properties; it never decides a rule.
import { SPECIES, FLOOR_DEPTH, zoneName, silhouetteSvg } from "./species.js";

const $ = (id) => document.getElementById(id);

export function starsSvg(n, of = 3) {
  let s = `<span class="stars" aria-label="${n} of ${of} stars">`;
  for (let i = 0; i < of; i++) {
    s += `<svg viewBox="0 0 24 24" class="${i < n ? "on" : ""}" aria-hidden="true"><path d="M12 2.8l2.8 6 6.5.7-4.9 4.4 1.4 6.4L12 17l-5.8 3.3 1.4-6.4L2.7 9.5l6.5-.7z"/></svg>`;
  }
  return `${s}</span>`;
}

export function createHud({ species, config }) {
  const els = {
    body: document.body,
    surface: $("surface"),
    hud: $("hud"),
    pause: $("pause"),
    results: $("results"),
    veil: $("veil"),
    grid: $("species-grid"),
    logCount: $("log-count"),
    best: $("best-line"),
    status: $("status"),
    diveStart: $("dive-start"),
    airNote: $("air-note"),
    diverName: $("diver-name"),
    title: $("title"),
    depth: $("depth"),
    zone: $("zone"),
    ruler: $("ruler"),
    rulerYou: $("ruler-you"),
    rulerReach: $("ruler-reach"),
    rulerMarks: $("ruler-marks"),
    airDial: $("air-dial"),
    airSecs: $("air-secs"),
    banner: $("banner"),
    strip: $("log-strip"),
    viewfinder: $("viewfinder"),
    vfRead: $("vf-read"),
    stick: $("stick"),
    stickKnob: $("stick-knob"),
    descend: $("descend-btn"),
    shutter: $("shutter-btn"),
    surfaceBtn: $("surface-btn"),
    surfaceLabel: $("surface-label"),
    soundBtn: $("sound-btn"),
    pauseBtn: $("pause-btn"),
    resume: $("resume-btn"),
    end: $("end-btn"),
    again: $("again-btn"),
    roll: $("roll"),
    resultsLede: $("results-lede"),
    tallyPhotos: $("tally-photos"),
    tallyStars: $("tally-stars"),
    tallyLog: $("tally-log"),
    tallyDepth: $("tally-depth"),
    viewer: $("viewer"),
    viewerImg: $("viewer-img"),
    viewerTitle: $("viewer-title"),
    viewerMeta: $("viewer-meta"),
    viewerSave: $("viewer-save"),
    viewerClose: $("viewer-close"),
    keysHint: $("keys-hint"),
  };
  const list = SPECIES.filter((s) => species.has(s.id));
  const total = list.length;

  els.title.textContent = config.title;
  document.title = config.title;
  els.diverName.textContent = config.diverName;
  els.airNote.textContent = `${config.airSeconds} seconds of air`;
  els.airDial.setAttribute("aria-valuemax", String(config.airSeconds));

  // Ruler marks at each band's middle.
  els.rulerMarks.innerHTML = list
    .map((s) => `<li class="ruler-mark" data-id="${s.id}" title="${s.name}"></li>`)
    .join("");
  for (const li of els.rulerMarks.children) {
    const s = list.find((x) => x.id === li.dataset.id);
    li.style.setProperty("--at", String((s.band[0] + s.band[1]) / 2 / FLOOR_DEPTH));
  }

  // Log strip slots.
  els.strip.innerHTML = list
    .map((s) => `<li class="slot" data-id="${s.id}" title="${s.name}, ${s.band[0]} to ${s.band[1]} m">${silhouetteSvg(s)}</li>`)
    .join("");

  let bannerTimer = 0;
  let lastDepth = -1;
  let lastAir = -1;

  const hud = {
    els,
    total,
    renderSurface(log) {
      els.grid.innerHTML = list
        .map((s) => {
          const rec = log.species[s.id];
          const art = rec && rec.thumb ? `<img src="${rec.thumb}" alt="" width="240" height="160">` : silhouetteSvg(s);
          return `<li class="species${rec ? " shot" : ""}">
            <div class="art">${art}</div>
            ${rec ? starsSvg(rec.stars) : ""}
            <p class="species-name" title="${s.name}">${s.short}</p>
            <p class="species-band">${s.band[0]}–${s.band[1]} m</p>
          </li>`;
        })
        .join("");
      const have = list.filter((s) => log.species[s.id]).length;
      els.logCount.textContent = `${have} of ${total} photographed`;
      if (log.best) {
        els.best.textContent = `Best dive: ${log.best.species} species, ${log.best.stars} ${log.best.stars === 1 ? "star" : "stars"}, down to ${log.best.depth} m.`;
      } else {
        els.best.textContent = "Six photos in one dive is a strong first dive. Your air includes the climb back up.";
      }
    },
    show(screen) {
      els.body.dataset.screen = screen;
      els.surface.hidden = screen !== "surface";
      els.hud.hidden = screen !== "dive";
      els.results.hidden = screen !== "results";
    },
    setPaused(p) {
      els.pause.hidden = !p;
      if (p) els.resume.focus();
    },
    veil(on) {
      els.veil.classList.toggle("on", on);
    },
    resetDive(log) {
      for (const li of els.strip.children) {
        li.className = "slot";
        li.querySelector("img")?.remove();
        li.querySelector(".stars")?.remove();
      }
      for (const li of els.rulerMarks.children) li.className = "ruler-mark";
      els.surfaceBtn.classList.remove("armed");
      els.surfaceLabel.textContent = "Surface";
      els.hud.classList.remove("breath");
      lastDepth = -1;
      lastAir = -1;
      void log;
    },
    banner(text, warn = false, ms = 2600) {
      els.banner.textContent = text;
      els.banner.classList.toggle("warn", warn);
      els.banner.classList.add("show");
      clearTimeout(bannerTimer);
      bannerTimer = setTimeout(() => els.banner.classList.remove("show"), ms);
    },
    keysHint(show) {
      els.keysHint.classList.toggle("show", show);
    },
    /** s: { depth, air, airTotal, reserve, reach, breath } */
    update(s) {
      const d = Math.round(s.depth);
      if (d !== lastDepth) {
        els.depth.value = String(d);
        els.depth.textContent = String(d);
        els.zone.textContent = zoneName(d);
        lastDepth = d;
      }
      els.rulerYou.style.setProperty("--y", (Math.min(s.depth, FLOOR_DEPTH) / FLOOR_DEPTH).toFixed(4));
      els.rulerReach.style.setProperty("--reach", (Math.min(s.reach, FLOOR_DEPTH) / FLOOR_DEPTH).toFixed(4));
      const a = Math.max(0, Math.ceil(s.air));
      if (a !== lastAir) {
        els.airSecs.value = String(a);
        els.airSecs.textContent = String(a);
        els.airDial.setAttribute("aria-valuenow", String(a));
        lastAir = a;
      }
      els.airDial.style.setProperty("--fill", ((s.air / s.airTotal) * 100).toFixed(2));
      els.airDial.style.setProperty("--reserve", ((Math.min(s.reserve, s.airTotal) / s.airTotal) * 100).toFixed(2));
      els.airDial.classList.toggle("low", s.air <= s.reserve + 8);
      els.hud.classList.toggle("breath", s.breath > 0.05);
    },
    markSpotted(id) {
      els.strip.querySelector(`[data-id="${id}"]`)?.classList.add("spotted");
      els.rulerMarks.querySelector(`[data-id="${id}"]`)?.classList.add("spotted");
    },
    markPhoto(id, thumb, stars) {
      const li = els.strip.querySelector(`[data-id="${id}"]`);
      if (!li) return;
      li.classList.add("spotted");
      li.querySelector("img")?.remove();
      li.querySelector(".stars")?.remove();
      li.insertAdjacentHTML("beforeend", `<img src="${thumb}" alt="" width="240" height="160">${starsSvg(stars)}`);
      li.classList.add("pop");
      setTimeout(() => li.classList.remove("pop"), 260);
      els.rulerMarks.querySelector(`[data-id="${id}"]`)?.classList.add("shot");
    },
    viewfinder(on, locked = false, text = "") {
      els.viewfinder.classList.toggle("on", on);
      els.hud.classList.toggle("vf", on);
      els.viewfinder.classList.toggle("locked", on && locked);
      els.vfRead.textContent = on ? text : "";
    },
    armSurface(armed) {
      els.surfaceBtn.classList.toggle("armed", armed);
      els.surfaceLabel.textContent = armed ? "Tap again to surface" : "Surface";
    },
    showResults(r) {
      els.resultsLede.textContent = r.lede;
      els.tallyPhotos.textContent = String(r.photos.length);
      els.tallyStars.textContent = String(r.stars);
      els.tallyLog.textContent = `${r.logged} of ${total}`;
      els.tallyDepth.textContent = `${r.depth} m`;
      els.roll.innerHTML = r.photos
        .map(
          (p, i) => `<li class="shot">
            <button class="shot-open" type="button" data-i="${i}" aria-label="Open the photo of ${p.name}"><img src="${p.url}" alt="${p.name} at ${p.depth} m" width="${p.w}" height="${p.h}"></button>
            <div class="shot-cap"><span class="shot-name">${p.name}</span>${starsSvg(p.stars)}</div>
            <button class="btn shot-save" type="button" data-save="${i}">Save photo</button>
          </li>`,
        )
        .join("");
    },
    openViewer(p) {
      els.viewerImg.src = p.url;
      els.viewerImg.alt = `${p.name} at ${p.depth} m`;
      els.viewerImg.width = p.w;
      els.viewerImg.height = p.h;
      els.viewerTitle.textContent = p.name;
      els.viewerMeta.textContent = `${p.depth} m down, ${p.dateText}. ${p.stars} of 3 stars.`;
      if (!els.viewer.open) els.viewer.showModal();
    },
  };
  return hud;
}
