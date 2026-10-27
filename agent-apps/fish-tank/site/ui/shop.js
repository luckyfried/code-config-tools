// The shop: a glass sheet that slides up over the tank, with fish, decor, and tank sizes. Each fish and each piece
// of decor shows live in its card.
import { offer } from "../sim/economy.js";

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat("en-US");

export function createShop({ catalog, theme, phone, getState, onBuy, onOpen, onClose }) {
  const sheet = $("shop");
  const scrim = $("scrim");
  const body = $("shopBody");
  const cards = $("shopCards");
  const button = $("shopBtn");
  let tab = "fish";
  let open = false;
  let views = [];

  const items = {
    fish: catalog.species.filter((s) => s.theme === theme).map((s) => ({ ...s, type: "fish" })),
    decor: catalog.decor.filter((d) => d.theme === theme || d.theme === "any").map((d) => ({ ...d, type: "decor" })),
    tank: catalog.tanks.map((t) => ({ ...t, type: "tank" })),
  };

  function lineFor(item, state) {
    if (item.type === "fish") {
      const have = state.fish.filter((f) => f.sp === item.id).length;
      const comes = item.buy > 1 ? `Comes as ${item.buy}` : "Comes alone";
      return [`${fmt.format(item.pph)} pearls an hour`, have ? `${have} in your tank` : comes];
    }
    if (item.type === "decor") return [item.kind === "bubbler" ? "A stream of bubbles" : item.theme === "any" ? "For any tank" : "For this tank"];
    const cap = phone ? Math.min(item.capacity, 30) : item.capacity;
    return [`Holds ${item.capacity} fish`, phone && item.capacity > 30 ? `A phone shows ${cap} of them` : "Room for a bigger school"];
  }

  function buyLabel(btn, item, verdict) {
    btn.replaceChildren();
    if (verdict.ok) {
      btn.append("Buy for ");
      const dot = document.createElement("span");
      dot.className = "pearl-dot";
      dot.setAttribute("aria-hidden", "true");
      btn.append(dot, fmt.format(item.price));
      btn.setAttribute("aria-label", `Buy ${item.name} for ${item.price} pearls`);
    } else {
      btn.append(verdict.reason);
      btn.removeAttribute("aria-label");
    }
    btn.disabled = !verdict.ok;
    btn.classList.toggle("is-owned", !!verdict.owned);
  }

  function render() {
    const state = getState();
    cards.replaceChildren();
    views = [];
    items[tab].forEach((item, i) => {
      const card = document.createElement("article");
      card.className = "card";
      card.style.setProperty("--i", String(i));
      const view = document.createElement("div");
      view.className = "card-view";
      if (item.type === "tank") {
        view.classList.add("card-view-tank");
        const sketch = document.createElement("div");
        sketch.className = "tank-sketch";
        sketch.style.width = `${40 + i * 30}%`;
        view.append(sketch);
      } else {
        views.push({ el: view, kind: item.type, id: item.id });
      }
      const text = document.createElement("div");
      text.className = "card-text";
      const name = document.createElement("h3");
      name.className = "card-name";
      name.textContent = item.name;
      text.append(name);
      for (const line of lineFor(item, state)) {
        const p = document.createElement("p");
        p.className = "card-line";
        p.textContent = line;
        text.append(p);
      }
      const wrap = document.createElement("div");
      wrap.className = "card-buy";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-buy";
      buyLabel(btn, item, offer(state, catalog, item, phone));
      btn.addEventListener("click", () => {
        if (onBuy(item)) render();
      });
      wrap.append(btn);
      text.append(wrap);
      card.append(view, text);
      cards.append(card);
    });
  }

  function setTab(next) {
    tab = next;
    for (const t of sheet.querySelectorAll(".tab")) t.setAttribute("aria-selected", String(t.dataset.tab === tab));
    body.scrollTop = 0;
    render();
  }

  function show() {
    if (open) return;
    open = true;
    render();
    sheet.classList.add("is-open");
    scrim.classList.add("is-open");
    sheet.removeAttribute("inert");
    sheet.setAttribute("aria-hidden", "false");
    button.setAttribute("aria-expanded", "true");
    onOpen();
    setTimeout(() => sheet.querySelector(".tab[aria-selected='true']")?.focus({ preventScroll: true }), 60);
  }

  function hide() {
    if (!open) return;
    open = false;
    sheet.classList.remove("is-open");
    scrim.classList.remove("is-open");
    sheet.setAttribute("inert", "");
    sheet.setAttribute("aria-hidden", "true");
    button.setAttribute("aria-expanded", "false");
    onClose();
  }

  for (const t of sheet.querySelectorAll(".tab")) t.addEventListener("click", () => setTab(t.dataset.tab));
  $("shopClose").addEventListener("click", hide);
  scrim.addEventListener("click", hide);
  button.addEventListener("click", () => (open ? hide() : show()));

  return {
    show, hide, render,
    toggle: () => (open ? hide() : show()),
    isOpen: () => open,
    views: () => views,
    clip: () => body.getBoundingClientRect(),
    refresh: () => { if (open) render(); },
  };
}
