// The Settings sheet: week start, theme, and the person's days saved to a file or loaded from one.
import { cleanData } from "./store.js";
import { dayKey } from "./dates.js";

export function createSheet({ dialog, opener, getState, onWeekStart, onTheme, onImport, onClearSample }) {
  const status = dialog.querySelector(".sheet-status");
  const clear = dialog.querySelector(".clear-sample");
  const file = dialog.querySelector(".import");
  let clearArmed = 0;

  const say = (text) => {
    status.textContent = text;
  };

  function sync() {
    const { weekStart, theme, data } = getState();
    dialog.querySelector(`input[name="weekStart"][value="${weekStart}"]`).checked = true;
    dialog.querySelector(`input[name="theme"][value="${theme}"]`).checked = true;
    clear.hidden = !data.sample;
    clear.textContent = "Clear the sample year";
    clearArmed = 0;
  }

  opener.addEventListener("click", () => {
    sync();
    say("");
    dialog.showModal();
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  dialog.addEventListener("change", (event) => {
    const input = event.target;
    if (input.name === "weekStart") onWeekStart(input.value);
    if (input.name === "theme") onTheme(input.value);
  });

  dialog.querySelector(".export").addEventListener("click", () => {
    const { data, habits } = getState();
    const body = {
      app: "habit-rings",
      saved: dayKey(new Date()),
      habits: habits.map(({ id, label }) => ({ id, label })),
      days: data.days,
      counts: data.counts,
    };
    const blob = new Blob([JSON.stringify(body, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "habit-rings.json";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    const n = Object.keys(data.days).length;
    say(`Saved habit-rings.json with ${n} ${n === 1 ? "day" : "days"}.`);
  });

  file.addEventListener("change", async () => {
    const chosen = file.files?.[0];
    file.value = "";
    if (!chosen) return;
    let data = null;
    try {
      data = cleanData(JSON.parse(await chosen.text()));
    } catch {
      data = null;
    }
    if (!data) {
      say(`${chosen.name} isn't a Habit Rings copy. Pick the habit-rings.json that Save a copy made.`);
      return;
    }
    data.sample = false;
    onImport(data);
    clear.hidden = true;
    const n = Object.keys(data.days).length;
    say(`Loaded ${n} ${n === 1 ? "day" : "days"} from ${chosen.name}.`);
  });

  clear.addEventListener("click", () => {
    if (!clearArmed) {
      clear.textContent = "Tap again to clear it";
      clearArmed = setTimeout(() => {
        clear.textContent = "Clear the sample year";
        clearArmed = 0;
      }, 4000);
      return;
    }
    clearTimeout(clearArmed);
    clearArmed = 0;
    onClearSample();
    clear.hidden = true;
    say("The sample is gone. Your year starts today.");
  });

  return { isOpen: () => dialog.open };
}
