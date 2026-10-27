// Pearls: what each fish earns, what a meal does, what the time away is worth, and what the shop sells.
// Pure functions over plain objects, so tests/economy.html checks them without a tank.

export const FED_MS = 10 * 60 * 1000; // a meal doubles a fish's pearls for ten minutes
export const FULL_MS = 90 * 1000; // and a fed fish turns down food for a minute and a half
export const FED_BOOST = 2;
export const AWAY_CAP_MS = 48 * 60 * 60 * 1000;
export const GROW_STEP = 0.03;
export const GROW_MAX = 1.3;
export const STARTING_PEARLS = 50;
export const PHONE_FISH = 30;

export function pearlsPerHour(spec, rate, rates, fed) {
  return spec.pph * (rates[rate] ?? 1) * (fed ? FED_BOOST : 1);
}

// seconds between two pearls from one fish
export function pearlInterval(spec, rate, rates, fed) {
  return 3600 / pearlsPerHour(spec, rate, rates, fed);
}

export function isFed(fish, now) {
  return (fish.fed || 0) > now;
}

export function isFull(fish, now) {
  return (fish.full || 0) > now;
}

// A meal: the fish grows a little, earns double for a while, and drops a pearl within a few seconds.
export function eat(fish, now, roll) {
  return {
    ...fish,
    g: Math.min(GROW_MAX, (fish.g || 1) + GROW_STEP),
    fed: now + FED_MS,
    full: now + FULL_MS,
    pin: Math.min(fish.pin ?? Infinity, 2.5 + roll * 5),
  };
}

// Pearls earned while the page was closed, at each fish's resting rate. A fraction of a pearl stays with the fish
// as its carry, so many short visits add up the same as one long one.
export function creditAway(fishList, speciesById, rate, rates, elapsedMs) {
  const ms = Math.max(0, Math.min(elapsedMs, AWAY_CAP_MS));
  const hours = ms / 3600000;
  let pearls = 0;
  const fish = fishList.map((f) => {
    const spec = speciesById[f.sp];
    if (!spec) return f;
    const exact = pearlsPerHour(spec, rate, rates, false) * hours + (f.carry || 0);
    const whole = Math.floor(exact + 1e-9);
    pearls += whole;
    return { ...f, carry: exact - whole };
  });
  return { pearls, hours, capped: elapsedMs > AWAY_CAP_MS, fish };
}

export function tankOf(catalog, id) {
  return catalog.tanks.find((t) => t.id === id) || catalog.tanks[0];
}

export function capacity(catalog, tankId, phone) {
  const cap = tankOf(catalog, tankId).capacity;
  return phone ? Math.min(cap, PHONE_FISH) : cap;
}

// What a shop card says about one item: whether it can be bought now, and the reason when it cannot.
export function offer(state, catalog, item, phone) {
  if (item.type === "tank") {
    const order = catalog.tanks.findIndex((t) => t.id === item.id);
    const have = catalog.tanks.findIndex((t) => t.id === state.tank);
    if (order <= have) return { ok: false, owned: true, reason: order === have ? "Your tank" : "Smaller than yours" };
    if (order > have + 1) return { ok: false, reason: `Get the ${catalog.tanks[have + 1].name.toLowerCase()} first` };
  } else if (item.type === "decor") {
    if (state.decor.includes(item.id)) return { ok: false, owned: true, reason: "In the tank" };
  } else {
    const room = capacity(catalog, state.tank, phone) - state.fish.length;
    if (room < 1) return { ok: false, reason: "The tank is full" };
  }
  if (state.pearls < item.price) return { ok: false, reason: `Need ${item.price - state.pearls} more` };
  return { ok: true };
}

export function buy(state, catalog, item, phone, now, makeId) {
  const verdict = offer(state, catalog, item, phone);
  if (!verdict.ok) return { state, added: [] };
  const next = { ...state, pearls: state.pearls - item.price };
  let added = [];
  if (item.type === "tank") next.tank = item.id;
  else if (item.type === "decor") next.decor = [...state.decor, item.id];
  else {
    const room = capacity(catalog, state.tank, phone) - state.fish.length;
    const n = Math.min(room, item.buy || 1);
    added = Array.from({ length: n }, (_, k) => newFish(item.id, now, makeId(), k));
    next.fish = [...state.fish, ...added];
  }
  return { state: next, added };
}

export function newFish(speciesId, now, id, k = 0) {
  return { id, sp: speciesId, g: 1, fed: 0, full: 0, pin: 20 + ((id * 7 + k * 13) % 30), carry: 0 };
}
