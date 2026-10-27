// The Day sheet (a mood and a one-line note), the Stats sheet, and the Export, import, and print sheet.
import { longDate, shortDate } from "./dates.js";
import { yearStats } from "./stats.js";

const $ = (id) => document.getElementById(id);
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

function wireClose(dialog) {
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog || e.target.closest("[data-close]")) dialog.close();
  });
}

export function createDaySheet(moods, { onSave, onClear }) {
  const dialog = $("day-sheet");
  const row = $("day-moods");
  const noteInput = $("day-note");
  const save = $("day-save");
  let day = null;
  let level = 0;

  const picks = moods.map((mood, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "mood-pick";
    b.setAttribute("role", "radio");
    const sw = document.createElement("span");
    sw.className = "mood-pick-swatch";
    sw.style.setProperty("--sw", `var(--mood-${i + 1})`);
    const name = document.createElement("span");
    name.textContent = mood.label;
    b.append(sw, name);
    b.addEventListener("click", () => choose(i + 1));
    return b;
  });
  row.replaceChildren(...picks);

  function choose(n) {
    level = n;
    picks.forEach((b, i) => {
      b.setAttribute("aria-checked", String(i + 1 === n));
      b.tabIndex = i + 1 === (n || 3) ? 0 : -1;
    });
    save.disabled = !n;
  }

  row.addEventListener("keydown", (e) => {
    const i = picks.indexOf(document.activeElement);
    if (i < 0) return;
    const step = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = (i + step + picks.length) % picks.length;
    choose(next + 1);
    picks[next].focus();
  });

  $("day-form").addEventListener("submit", (e) => {
    if (!level) {
      e.preventDefault();
      return;
    }
    onSave(day, level, noteInput.value);
  });
  $("day-clear").addEventListener("click", () => {
    onClear(day);
    dialog.close();
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  return {
    open(target, entry) {
      day = target;
      $("day-title").textContent = longDate(day);
      noteInput.value = entry && entry.note ? entry.note : "";
      choose(entry ? entry.mood : 0);
      $("day-clear").hidden = !entry;
      dialog.showModal();
      if (entry) noteInput.focus();
      else picks[2].focus();
    },
  };
}

export function createStatsSheet(moods) {
  const dialog = $("stats-sheet");
  wireClose(dialog);

  function fill(days, year, weekStart, today) {
    const s = yearStats(days, year, weekStart);
    const inYear = today.startsWith(String(year));
    $("stats-title").textContent = inYear ? `${year} so far` : String(year);

    const max = Math.max(1, ...s.counts.slice(1));
    $("stat-moods").replaceChildren(
      ...moods
        .map((mood, i) => {
          const n = i + 1;
          const li = document.createElement("li");
          li.className = "stat-mood";
          li.style.setProperty("--sw", `var(--mood-${n})`);
          li.style.setProperty("--share", String(s.counts[n] / max));
          const sw = document.createElement("span");
          sw.className = "stat-swatch";
          const label = document.createElement("span");
          label.className = "stat-label";
          label.textContent = mood.label;
          const count = document.createElement("span");
          count.className = "stat-count";
          count.textContent = plural(s.counts[n], "day");
          const bar = document.createElement("span");
          bar.className = "stat-bar";
          const run = document.createElement("span");
          run.className = "stat-run";
          const r = s.runs[n];
          run.textContent = !r
            ? "No days yet"
            : r.len === 1
              ? `Longest run: one day, ${shortDate(r.start)}`
              : `Longest run: ${r.len} days, ${shortDate(r.start)} to ${shortDate(r.end)}`;
          li.append(sw, label, count, bar, run);
          return li;
        })
        .reverse(),
    );

    const best = s.best;
    $("stat-best").textContent = best
      ? `${best.name} was the best month, with ${plural(best.high, "day")} of ${moods[3].label} or ${moods[4].label}.`
      : "Color a few more days and the best month shows here.";

    $("stat-week").replaceChildren(
      ...s.weekdays.map((w) => {
        const el = document.createElement("div");
        el.className = "weekday";
        const tile = document.createElement("span");
        tile.className = "weekday-tile";
        if (w.avg) tile.style.setProperty("--sw", `var(--mood-${Math.round(w.avg)})`);
        const name = document.createElement("span");
        name.textContent = w.name;
        el.title = w.avg ? `${w.name}: most often ${moods[Math.round(w.avg) - 1].label}` : w.name;
        el.append(tile, name);
        return el;
      }),
    );
  }

  return {
    open(days, year, weekStart, today) {
      fill(days, year, weekStart, today);
      dialog.showModal();
    },
  };
}

export function createSettingsSheet(config, { onExport, onImport, onClear }) {
  const dialog = $("settings-sheet");
  const clear = $("clear");
  const importText = $("import-text");
  const importNote = importText.textContent;
  let year = config.year;
  let armed = false;
  wireClose(dialog);

  $("paper-text").textContent = `${config.paper === "Letter" ? "A US Letter" : `An ${config.paper}`} poster of the year with your name, ready for the printer.`;
  $("print").addEventListener("click", () => {
    dialog.close();
    requestAnimationFrame(() => window.print());
  });
  $("export").addEventListener("click", onExport);
  $("import").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    importText.textContent = await onImport(file);
  });

  function disarm() {
    armed = false;
    $("clear-name").textContent = `Clear ${year}`;
    clear.textContent = `Clear ${year}`;
  }
  clear.addEventListener("click", () => {
    if (!armed) {
      armed = true;
      clear.textContent = `Yes, clear ${year}`;
      return;
    }
    onClear(year);
    disarm();
    dialog.close();
  });

  return {
    open(viewYear) {
      year = viewYear;
      importText.textContent = importNote;
      disarm();
      dialog.showModal();
    },
  };
}
