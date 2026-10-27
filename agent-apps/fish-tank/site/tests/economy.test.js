// Pearl math: away credit at each rate, the 48 hour cap, the carry that keeps short visits fair, meals, and the shop.
import { creditAway, eat, isFed, isFull, buy, offer, newFish, FED_MS, FULL_MS, GROW_MAX } from "../sim/economy.js";
import { createReport } from "./report.js";

const report = createReport();
const catalog = await (await fetch("../sim/catalog.json")).json();
const byId = Object.fromEntries(catalog.species.map((s) => [s.id, s]));
const HOUR = 3600000;
const tank = [newFish("clownfish", 0, 1), newFish("clownfish", 0, 2), newFish("blue-tang", 0, 3)];

const eight = creditAway(tank, byId, "normal", catalog.rates, 8 * HOUR);
report.check("2 clownfish and 1 blue tang make 272 pearls in 8 hours at the normal rate", eight.pearls === 272, `${eight.pearls}`);

const fast = creditAway(tank, byId, "fast", catalog.rates, 8 * HOUR);
report.check("the fast rate makes 488 pearls and keeps the fractions as carry", fast.pearls === 488 && fast.fish.every((f) => f.carry >= 0 && f.carry < 1), `${fast.pearls}`);

const calm = creditAway(tank, byId, "calm", catalog.rates, 8 * HOUR);
report.check("the calm rate makes fewer pearls than normal", calm.pearls < eight.pearls, `${calm.pearls}`);

const capped = creditAway(tank, byId, "normal", catalog.rates, 72 * HOUR);
report.check("72 hours away pays for 48", capped.pearls === 34 * 48 && capped.capped, `${capped.pearls}`);

let list = tank;
let total = 0;
for (let k = 0; k < 48; k++) {
  const r = creditAway(list, byId, "normal", catalog.rates, 10 * 60000);
  total += r.pearls;
  list = r.fish;
}
report.check("48 visits of 10 minutes pay the same as one visit of 8 hours", total === 272, `${total}`);

const fed = eat(tank[0], 1000, 0.5);
report.check("a meal makes the fish full, fed, a little bigger, and due a pearl within 8 seconds",
  isFull(fed, 1000 + FULL_MS - 1) && !isFull(fed, 1000 + FULL_MS + 1) && isFed(fed, 1000 + FED_MS - 1) && fed.g > 1 && fed.pin <= 7.5);
let grown = tank[0];
for (let k = 0; k < 40; k++) grown = eat(grown, k, 0);
report.check("a fish stops growing at its full size", grown.g === GROW_MAX, `${grown.g}`);

const state = { pearls: 100, tank: "small", decor: ["staghorn"], fish: [...tank], nextId: 4 };
let id = 10;
const tetra = { ...catalog.species.find((s) => s.id === "green-chromis"), type: "fish" };
const bought = buy(state, catalog, tetra, false, 0, () => id++);
report.check("buying green chromis adds three fish and takes the price", bought.added.length === 3 && bought.state.pearls === 100 - tetra.price);
report.check("decor already in the tank is not sold twice", !offer(state, catalog, { ...catalog.decor[0], type: "decor" }, false).ok);
const big = { ...catalog.tanks[2], type: "tank" };
report.check("the large tank waits for the medium one", offer({ ...state, pearls: 9999 }, catalog, big, false).reason === "Get the medium tank first");
const full = { ...state, tank: "large", pearls: 9999, fish: Array.from({ length: 30 }, (_, k) => newFish("clownfish", 0, k)) };
report.check("a phone tank holds 30 fish", !offer(full, catalog, tetra, true).ok && offer(full, catalog, tetra, false).ok);
report.done();
