// The Settings sheet: the place (search by name), the map's reach, the layers, the loop speed, and the units.
import { searchPlaces } from "../data/feeds.js";

const $ = (id) => document.getElementById(id);

export function createSettings(state, { onChange }) {
  const dialog = $("settings");
  const search = $("placeSearch");
  const results = $("placeResults");
  const note = $("placeNote");

  const reflect = () => {
    for (const group of dialog.querySelectorAll(".segmented")) {
      const value = state[group.dataset.name];
      for (const b of group.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.value === value));
    }
    for (const b of dialog.querySelectorAll(".toggle")) b.setAttribute("aria-pressed", String(state.layers.includes(b.dataset.layer)));
    $("placeNow").textContent = state.place.name;
  };

  $("openSettings").addEventListener("click", () => {
    reflect();
    dialog.showModal();
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  dialog.addEventListener("click", (e) => {
    const seg = e.target.closest(".segmented button");
    if (seg) {
      const name = seg.closest(".segmented").dataset.name;
      if (state[name] !== seg.dataset.value) {
        state[name] = seg.dataset.value;
        reflect();
        onChange(name);
      }
      return;
    }
    const toggle = e.target.closest(".toggle");
    if (toggle) {
      const layer = toggle.dataset.layer;
      state.layers = state.layers.includes(layer) ? state.layers.filter((l) => l !== layer) : [...state.layers, layer];
      reflect();
      onChange("layers");
      return;
    }
    const pick = e.target.closest("[data-lat]");
    if (pick) {
      state.place = { name: pick.dataset.name, lat: Number(pick.dataset.lat), lon: Number(pick.dataset.lon) };
      results.replaceChildren();
      search.value = "";
      reflect();
      onChange("place");
    }
  });

  let timer = 0;
  let asked = 0;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    const q = search.value.trim();
    note.hidden = true;
    if (q.length < 2) {
      results.replaceChildren();
      return;
    }
    timer = setTimeout(async () => {
      const mine = ++asked;
      try {
        const found = await searchPlaces(q);
        if (mine !== asked) return;
        results.replaceChildren(
          ...found.map((p) => {
            const li = document.createElement("li");
            const b = document.createElement("button");
            b.type = "button";
            b.dataset.lat = p.lat;
            b.dataset.lon = p.lon;
            b.dataset.name = p.where ? `${p.name}, ${p.where.split(",")[0]}` : p.name;
            b.textContent = p.name;
            const small = document.createElement("small");
            small.textContent = p.where;
            b.append(small);
            li.append(b);
            return li;
          }),
        );
        if (!found.length) {
          note.textContent = `No town called “${q}”.`;
          note.hidden = false;
        }
      } catch {
        if (mine !== asked) return;
        results.replaceChildren();
        note.textContent = "Place search needs an internet connection.";
        note.hidden = false;
      }
    }, 320);
  });

  reflect();
  return { reflect };
}
