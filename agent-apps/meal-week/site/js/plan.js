// The plan as the page reads it: weeks in date order, each week's grocery list merged by name and unit,
// and the words and numbers the tiles and the list print.

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December"];
const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// Ten edge colors (--edge-1 to --edge-10). Each cuisine has the color it prefers; within one week no two
// cuisines share a color, so a cuisine whose color is taken moves to the next free one.
const EDGES = 10;
const CUISINE_EDGE = {
  italian: 1, spanish: 1, peruvian: 1,
  mexican: 2, "tex-mex": 2, cajun: 2, southern: 2,
  indian: 3, moroccan: 3, ethiopian: 3,
  vegetarian: 4, caribbean: 4, korean: 4,
  thai: 5, vietnamese: 5,
  mediterranean: 6, greek: 6, seafood: 6,
  japanese: 7, chinese: 7,
  french: 8, british: 8, german: 8,
  "middle eastern": 9, persian: 9, lebanese: 9, turkish: 9,
  american: 10,
};

export const keyOf = (name) => name.trim().replace(/\s+/g, " ").toLowerCase();

function preferredEdge(key) {
  if (CUISINE_EDGE[key]) return CUISINE_EDGE[key];
  let h = 0;
  for (const ch of key) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return (h % EDGES) + 1;
}

// The week's cuisines in the order they first appear, each with its own color while there are colors left.
function weekEdges(days) {
  const edges = new Map();
  const taken = new Set();
  for (const day of days) {
    for (const { meal } of day.meals) {
      const key = keyOf(meal?.cuisine || "");
      if (!meal || !key || edges.has(key)) continue;
      let edge = preferredEdge(key);
      for (let n = 0; n < EDGES && taken.has(edge); n += 1) edge = (edge % EDGES) + 1;
      edges.set(key, edge);
      taken.add(edge);
    }
  }
  return edges;
}

const parseDay = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};
const addDays = (date, n) => new Date(date.getTime() + n * 86400000);
const dayOfMonth = (date) => date.getUTCDate();
const monthOf = (date) => MONTHS[date.getUTCMonth()];

export function range(weekOf) {
  const start = parseDay(weekOf);
  const end = addDays(start, 6);
  const a = `${monthOf(start).slice(0, 3)} ${dayOfMonth(start)}`;
  const b = start.getUTCMonth() === end.getUTCMonth() ? `${dayOfMonth(end)}` : `${monthOf(end).slice(0, 3)} ${dayOfMonth(end)}`;
  return `${a} to ${b}`;
}

export function longRange(weekOf) {
  const start = parseDay(weekOf);
  const end = addDays(start, 6);
  return `${monthOf(start)} ${dayOfMonth(start)} to ${monthOf(end)} ${dayOfMonth(end)}, ${end.getUTCFullYear()}`;
}

export function buildWeeks(config) {
  const slots = config.slots;
  const all = [{ weekOf: config.weekOf, name: config.name, days: config.days }, ...(config.otherWeeks || [])];
  const pantry = new Set((config.pantry || []).map(keyOf));
  const today = new Date();
  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return all
    .map((w) => {
      const start = parseDay(w.weekOf);
      const days = w.days.map((d, i) => {
        const date = addDays(start, i);
        const iso = date.toISOString().slice(0, 10);
        return {
          index: i,
          short: DAY_SHORT[i],
          long: DAY_LONG[i],
          date: dayOfMonth(date),
          month: monthOf(date),
          isToday: iso === todayIso,
          meals: slots.map((slot) => ({ slot, meal: (d.meals || {})[slot] || null })),
        };
      });
      const edges = weekEdges(days);
      for (const day of days) for (const m of day.meals) m.edge = m.meal ? edges.get(keyOf(m.meal.cuisine || "")) || 0 : 0;
      return {
        weekOf: w.weekOf,
        name: w.name || `Week of ${monthOf(start)} ${dayOfMonth(start)}`,
        days,
        list: mergeList(days, config.aisles, pantry),
      };
    })
    .sort((a, b) => a.weekOf.localeCompare(b.weekOf));
}

// One item per ingredient name (less the pantry); its lines are one per unit, the same unit summed.
function mergeList(days, aisles, pantry) {
  const items = new Map();
  for (const day of days) {
    for (const { meal } of day.meals) {
      if (!meal) continue;
      for (const ing of meal.ingredients || []) {
        const key = keyOf(ing.name);
        if (pantry.has(key)) continue;
        if (!items.has(key)) items.set(key, { key, name: ing.name.trim(), aisle: ing.aisle, lines: new Map(), meals: new Set() });
        const item = items.get(key);
        const unit = (ing.unit || "").trim().toLowerCase();
        item.lines.set(unit, (item.lines.get(unit) || 0) + ing.amount);
        item.meals.add(meal.name);
      }
    }
  }
  const byAisle = aisles.map((aisle) => ({ aisle, items: [] }));
  for (const item of items.values()) {
    const group = byAisle.find((g) => g.aisle === item.aisle);
    group.items.push({
      key: item.key,
      name: item.name,
      lines: [...item.lines].map(([unit, amount]) => quantity(amount, unit)),
      meals: [...item.meals],
    });
  }
  for (const group of byAisle) group.items.sort((a, b) => a.name.localeCompare(b.name));
  const groups = byAisle.filter((g) => g.items.length);
  return { groups, count: items.size };
}

const FRACTIONS = [[0.25, "¼"], [0.333, "⅓"], [0.5, "½"], [0.667, "⅔"], [0.75, "¾"]];
const NO_PLURAL = new Set(["g", "kg", "ml", "l", "oz", "lb", "tbsp", "tsp", "fl oz"]);

export function amountText(n) {
  const whole = Math.floor(n + 1e-9);
  const rest = n - whole;
  if (rest < 0.01) return String(whole);
  const frac = FRACTIONS.find(([v]) => Math.abs(v - rest) < 0.02);
  if (frac) return whole ? `${whole}${frac[1]}` : frac[1];
  return String(Math.round(n * 100) / 100);
}

export function unitText(unit, amount) {
  if (!unit || NO_PLURAL.has(unit) || amount <= 1) return unit;
  if (/(ch|sh|s|x)$/.test(unit)) return `${unit}es`;
  return `${unit}s`;
}

export function quantity(amount, unit) {
  const a = amountText(amount);
  const u = unitText(unit, amount);
  return u ? `${a} ${u}` : a;
}

export function minutesText(min) {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h} hr ${m} min` : `${h} hr`;
}

export const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
