// The plant drawings: one sprite of eight silhouettes and a neutral leaf, drawn inside the soil ring and its pot.
export const TYPES = ["fern", "succulent", "vine", "palm", "fiddle", "cactus", "herb", "orchid"];

const ALIASES = {
  fern: "fern", bostonfern: "fern", maidenhair: "fern", birdsnest: "fern", staghorn: "fern", asparagus: "fern",
  succulent: "succulent", echeveria: "succulent", jade: "succulent", aloe: "succulent", haworthia: "succulent",
  sedum: "succulent", kalanchoe: "succulent", crassula: "succulent", agave: "succulent", sansevieria: "succulent",
  snakeplant: "succulent", zz: "succulent", zamioculcas: "succulent",
  vine: "vine", trailingvine: "vine", trailing: "vine", pothos: "vine", ivy: "vine", philodendron: "vine",
  scindapsus: "vine", hoya: "vine", tradescantia: "vine", wanderingdude: "vine", stringofpearls: "vine",
  stringofhearts: "vine", creeping: "vine", syngonium: "vine", arrowhead: "vine",
  palm: "palm", kentia: "palm", parlorpalm: "palm", areca: "palm", dracaena: "palm", yucca: "palm",
  spiderplant: "palm", chlorophytum: "palm", ponytail: "palm", schefflera: "palm", umbrella: "palm", bromeliad: "palm",
  fiddle: "fiddle", fiddleleaf: "fiddle", fiddleleaffig: "fiddle", fig: "fiddle", ficus: "fiddle", rubber: "fiddle",
  rubberplant: "fiddle", monstera: "fiddle", swisscheese: "fiddle", calathea: "fiddle", maranta: "fiddle",
  prayerplant: "fiddle", aglaonema: "fiddle", chineseevergreen: "fiddle", alocasia: "fiddle", elephantear: "fiddle",
  birdofparadise: "fiddle", strelitzia: "fiddle", croton: "fiddle", dieffenbachia: "fiddle", banana: "fiddle",
  cactus: "cactus", cacti: "cactus", opuntia: "cactus", pricklypear: "cactus", bunnyears: "cactus", mammillaria: "cactus",
  herb: "herb", basil: "herb", mint: "herb", rosemary: "herb", parsley: "herb", thyme: "herb", oregano: "herb",
  sage: "herb", cilantro: "herb", coriander: "herb", chives: "herb", dill: "herb", lavender: "herb", pilea: "herb",
  peperomia: "herb", begonia: "herb", coleus: "herb", fittonia: "herb",
  orchid: "orchid", phalaenopsis: "orchid", mothorchid: "orchid", peacelily: "orchid", spathiphyllum: "orchid",
  anthurium: "orchid", africanviolet: "orchid", saintpaulia: "orchid", amaryllis: "orchid", christmascactus: "orchid",
  geranium: "orchid", lily: "orchid",
};
// Longest first, so "christmascactus" wins over "cactus" and "fiddleleaffig" over "fig".
const ALIAS_KEYS = Object.keys(ALIASES).sort((a, b) => b.length - a.length);

const lookup = (word) => {
  const key = String(word ?? "").toLowerCase().replace(/[^a-z]/g, "");
  if (!key) return null;
  if (ALIASES[key]) return ALIASES[key];
  const part = ALIAS_KEYS.find((alias) => key.includes(alias));
  return part ? ALIASES[part] : null;
};

/** The drawing a type picks, then the plant's name; anything the sprite has no drawing of gets the neutral leaf. */
export function drawingFor(type, name = "") {
  return lookup(type) ?? lookup(name) ?? "leaf";
}

const symbols = new Map();

export async function loadSprite(url) {
  const text = await (await fetch(url)).text();
  const doc = new DOMParser().parseFromString(text, "image/svg+xml");
  for (const symbol of doc.querySelectorAll("symbol")) symbols.set(symbol.id, symbol.innerHTML);
}

const plantBody = (drawing) => symbols.get(drawing) ?? symbols.get("leaf") ?? "";

/** The soil ring, the pot, the plant, and the droplet that falls when it is watered. `initial` is lettered on the pot. */
export function ringMarkup(drawing, initial = "") {
  return `<svg class="ring" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
<circle class="ring-face" cx="50" cy="50" r="43.5"/>
<circle class="ring-track f-part" cx="50" cy="50" r="46.5"/>
<circle class="ring-bar f-part" cx="50" cy="50" r="46.5" pathLength="100" transform="rotate(-90 50 50)"/>
<path class="pot-body" d="M33 66L67 66L63.6 85.6Q63.2 88 60.8 88L39.2 88Q36.8 88 36.4 85.6Z"/>
<path class="pot-band" d="M34.1 71.5L65.9 71.5L65.5 74L34.5 74Z"/>
<rect class="pot-rim" x="30" y="59" width="40" height="7.5" rx="1.6"/>
${initial ? `<text class="pot-initial" x="50" y="85" text-anchor="middle">${initial}</text>` : ""}
<ellipse class="soil f-part" cx="50" cy="61" rx="17.6" ry="2.3"/>
<g class="plant">${plantBody(drawing)}</g>
<ellipse class="ripple" cx="50" cy="61.5" rx="7" ry="1.8"/>
<path class="drop" d="M50 3C50 3 44.6 10.6 44.6 14.2A5.4 5.4 0 0 0 55.4 14.2C55.4 10.6 50 3 50 3Z"/>
</svg>`;
}

/** A small plant for the schedule, cropped to the leaves. */
export function miniMarkup(drawing) {
  return `<svg viewBox="10 6 80 80" aria-hidden="true" focusable="false"><g class="plant">${plantBody(drawing)}</g></svg>`;
}

/** Sets a ring's drained share on the card (or sheet) and on each ring part that reads it. */
export function setFill(root, f) {
  const value = String(Math.min(f, 1.2));
  root.style.setProperty("--f", value);
  for (const part of root.querySelectorAll(".f-part")) part.style.setProperty("--f", value);
}
