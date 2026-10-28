// What the rails and sheets show: the mode switch, the stats, how to play, and the settings. Each renders into
// every container that asks for it, so the desktop rails and the phone sheets always agree.

import { winRate } from "../game/stats.js";

const PALETTES = {
  paper: { name: "Paper", art: ["#EBEDE6", "#628D60", "#CC9A3A", "#1A2130"] },
  night: { name: "Night", art: ["#05110D", "#1FC07F", "#F5AA2C", "#14271F"] },
  candy: { name: "Candy", art: ["#FFE6F0", "#1BC48C", "#FFC33A", "#E0307F"] },
};

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function renderModes(mode, onPick) {
  document.querySelectorAll("[data-modes]").forEach((box) => {
    if (!box.childElementCount) {
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", "Mode");
      box.innerHTML = `<button class="mode-btn" type="button" data-mode="daily">Daily</button><button class="mode-btn" type="button" data-mode="endless">Endless</button>`;
      box.addEventListener("click", (event) => {
        const b = event.target.closest("[data-mode]");
        if (b) onPick(b.dataset.mode);
      });
    }
    box.dataset.mode = mode;
    box.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  });
}

// Before the first daily game there is nothing to chart: one line, and the week's streak as seven empty sockets.
const FIRST_HTML = `
    <div class="first-card">
      <p class="first-line">Your first word is waiting.</p>
      <div class="first-streak">
        <span class="streak-marks" aria-hidden="true">${"<i></i>".repeat(7)}</span>
        <span class="stat-label">Streak starts with today's word</span>
      </div>
    </div>`;

export function renderStats(stats, { highlight = 0 } = {}) {
  const most = Math.max(1, ...stats.dist);
  const html = !stats.played ? FIRST_HTML : `
    <div class="stat-grid">
      <div class="stat"><span class="stat-value">${stats.played}</span><span class="stat-label">Played</span></div>
      <div class="stat"><span class="stat-value">${winRate(stats)}<small>%</small></span><span class="stat-label">Win rate</span></div>
      <div class="stat"><span class="stat-value">${stats.streak}</span><span class="stat-label">Streak</span></div>
      <div class="stat"><span class="stat-value">${stats.best}</span><span class="stat-label">Best streak</span></div>
    </div>
    <div class="dist" role="list" aria-label="Guess distribution">
      ${stats.dist
        .map((n, i) => {
          const f = n ? Math.max(0.1, n / most) : 0;
          const cls = ["dist-row", highlight === i + 1 ? "is-best" : "", n ? "" : "is-empty"].join(" ").trim();
          const say = `${n} ${n === 1 ? "win" : "wins"} in ${i + 1}`;
          return `<div class="${cls}" role="listitem" aria-label="${say}" data-f="${f.toFixed(3)}"><span class="dist-n" aria-hidden="true">${i + 1}</span><span class="dist-track" aria-hidden="true"><i class="dist-bar"></i>${n ? `<span class="dist-count">${n}</span>` : ""}</span></div>`;
        })
        .join("")}
    </div>`;
  document.querySelectorAll('[data-panel="stats"]').forEach((box) => {
    box.innerHTML = html;
    box.querySelectorAll(".dist-row").forEach((row) => {
      row.style.setProperty("--f", "0");
      requestAnimationFrame(() => requestAnimationFrame(() => row.style.setProperty("--f", row.dataset.f)));
    });
  });
}

function miniRow(word, marks) {
  return `<div class="mini-row" aria-hidden="true">${[...word]
    .map((ch, i) => `<span class="mini"${marks[i] ? ` data-result="${marks[i]}"` : ""}>${ch}</span>`)
    .join("")}</div>`;
}

export function renderHelp() {
  const html = `
    <p class="rules">Guess the word in <strong>six tries</strong>. Each guess is a five-letter word; press Enter to check it. The tiles turn to show how close you are.</p>
    <div class="examples">
      <div class="example">${miniRow("WHIRL", ["correct"])}<p><strong>W</strong> is in the word and in the right spot.</p></div>
      <div class="example">${miniRow("CABIN", [null, "present"])}<p><strong>A</strong> is in the word, in another spot.</p></div>
      <div class="example">${miniRow("PLUMB", [null, null, "absent"])}<p><strong>U</strong> is not in the word.</p></div>
    </div>
    <p class="rules examples rules-more">A new word arrives every midnight. Endless deals a fresh word whenever you want one.</p>`;
  document.querySelectorAll('[data-panel="help"]').forEach((box) => {
    box.innerHTML = html;
  });
}

export function renderSettings(settings, { hardLocked }, onChange) {
  const sw = (key, on, disabled = false) =>
    `<button class="switch" type="button" role="switch" aria-checked="${on}" data-setting="${key}"${disabled ? " disabled" : ""} aria-label="${key === "hardMode" ? "Hard mode" : key === "highContrast" ? "High contrast" : "Sound"}"></button>`;
  const scheme = settings.scheme || "auto";
  const palette = settings.palette || "";
  const html = `
    <div class="settings-list">
      <div class="setting">
        <div class="setting-text"><div class="setting-name">Hard mode</div><div class="setting-note">${hardLocked ? "Change it before your first guess." : "Use every letter you've found."}</div></div>
        ${sw("hardMode", !!settings.hardMode, hardLocked)}
      </div>
      <div class="setting">
        <div class="setting-text"><div class="setting-name">High contrast</div><div class="setting-note">Orange and blue tiles.</div></div>
        ${sw("highContrast", !!settings.highContrast)}
      </div>
      <div class="setting">
        <div class="setting-text"><div class="setting-name">Sound</div></div>
        ${sw("sound", settings.sound !== false)}
      </div>
      <div class="setting">
        <div class="setting-text"><div class="setting-name">Theme</div></div>
        <div class="choice" role="group" aria-label="Theme">
          ${["auto", "light", "dark"].map((s) => `<button type="button" data-scheme="${s}" aria-pressed="${scheme === s}">${s[0].toUpperCase() + s.slice(1)}</button>`).join("")}
        </div>
      </div>
      <div class="setting">
        <div class="setting-text"><div class="setting-name">Palette</div><div class="setting-note">${esc(PALETTES[palette]?.name || "As set up")}</div></div>
        <div class="swatches" role="group" aria-label="Palette">
          ${Object.entries(PALETTES)
            .map(([id, p]) => `<button class="swatch" type="button" data-palette="${id}" aria-pressed="${palette === id}" aria-label="${p.name}"><span class="swatch-art"><i></i><i></i><i></i><i></i></span></button>`)
            .join("")}
        </div>
      </div>
    </div>`;
  document.querySelectorAll('[data-panel="settings"]').forEach((box) => {
    box.innerHTML = html;
    box.querySelectorAll("[data-palette]").forEach((b) => {
      const art = PALETTES[b.dataset.palette].art;
      b.querySelectorAll(".swatch-art i").forEach((cell, i) => cell.style.setProperty("--swatch", art[i]));
    });
    if (!box.dataset.wired) {
      box.dataset.wired = "1";
      box.addEventListener("click", (event) => {
        const s = event.target.closest("[data-setting]");
        if (s && !s.disabled) return onChange({ [s.dataset.setting]: s.getAttribute("aria-checked") !== "true" });
        const c = event.target.closest("[data-scheme]");
        if (c) return onChange({ scheme: c.dataset.scheme });
        const p = event.target.closest("[data-palette]");
        if (p) return onChange({ palette: p.dataset.palette });
      });
    }
  });
}

export function miniAnswer(word) {
  return miniRow(word, [...word].map(() => "correct"));
}
