// Problems by operation and level (1 to 10). Every answer is a whole number of zero or more.

export const OPERATIONS = ["add", "subtract", "multiply", "divide", "percent", "squares"];
export const MIN_LEVEL = 1;
export const MAX_LEVEL = 10;

export const OP_LABELS = {
  add: { symbol: "+", name: "Add" },
  subtract: { symbol: "−", name: "Subtract" },
  multiply: { symbol: "×", name: "Multiply" },
  divide: { symbol: "÷", name: "Divide" },
  percent: { symbol: "%", name: "Percent" },
  squares: { symbol: "x²", name: "Squares" },
};

const int = (rand, lo, hi) => lo + Math.floor(rand() * (hi - lo + 1));
const pick = (rand, list) => list[Math.floor(rand() * list.length)];

// Operand ranges for add and subtract, by level.
const SUMS = [
  [[1, 5], [1, 5]],
  [[1, 9], [1, 9]],
  [[10, 30], [2, 9]],
  [[10, 60], [10, 40]],
  [[20, 99], [20, 99]],
  [[100, 400], [11, 99]],
  [[100, 500], [100, 500]],
  [[100, 999], [100, 999]],
  [[1000, 5000], [100, 999]],
  [[1000, 9999], [1000, 9999]],
];

// Factor ranges for multiply and divide, by level.
const PRODUCTS = [
  [[1, 5], [1, 5]],
  [[2, 10], [2, 2], [5, 5], [10, 10]],
  [[2, 10], [2, 10]],
  [[2, 12], [2, 12]],
  [[11, 25], [2, 9]],
  [[20, 99], [2, 9]],
  [[11, 19], [11, 19]],
  [[12, 30], [11, 25]],
  [[100, 999], [2, 9]],
  [[20, 99], [20, 99]],
];

const PERCENTS = [
  { p: [50, 10], base: [2, 100] },
  { p: [50, 10, 25, 100], base: [4, 120] },
  { p: [10, 20, 25, 50], base: [10, 200] },
  { p: [5, 10, 20, 25, 50, 75], base: [20, 400] },
  { p: [5, 10, 15, 20, 25, 30, 40, 60, 75], base: [20, 500] },
  { p: [5, 15, 35, 45, 55, 65, 85, 95], base: [100, 900] },
  { p: "any", base: [100, 1000] },
  { p: [12, 15, 18, 35, 45, 64, 72, 85], base: [50, 1000] },
  { p: "any", base: [50, 2000] },
  { p: "any", base: [100, 5000] },
];

const SQUARES = [[1, 5], [1, 10], [1, 12], [2, 15], [5, 20], [10, 25], [11, 30], [20, 50], [30, 70], [40, 99]];

function sum(rand, level) {
  const [ra, rb] = SUMS[level - 1];
  return [int(rand, ...ra), int(rand, ...rb)];
}

function product(rand, level) {
  const ranges = PRODUCTS[level - 1];
  const a = int(rand, ...ranges[0]);
  const b = int(rand, ...pick(rand, ranges.slice(1)));
  return rand() < 0.5 ? [a, b] : [b, a];
}

function percent(rand, level) {
  const spec = PERCENTS[level - 1];
  for (let tries = 0; tries < 200; tries += 1) {
    const p = spec.p === "any" ? int(rand, 2, 98) : pick(rand, spec.p);
    const base = int(rand, ...spec.base);
    if ((p * base) % 100 === 0 && p * base > 0) return [p, base, (p * base) / 100];
  }
  return [10, 100, 10];
}

const GENERATORS = {
  add(rand, level) {
    const [a, b] = sum(rand, level);
    return { text: `${a} + ${b}`, answer: a + b };
  },
  subtract(rand, level) {
    const [x, y] = sum(rand, level);
    const a = Math.max(x, y);
    const b = Math.min(x, y);
    return { text: `${a} − ${b}`, answer: a - b };
  },
  multiply(rand, level) {
    const [a, b] = product(rand, level);
    return { text: `${a} × ${b}`, answer: a * b };
  },
  divide(rand, level) {
    const [a, b] = product(rand, level);
    const divisor = Math.max(1, b);
    return { text: `${a * divisor} ÷ ${divisor}`, answer: a };
  },
  percent(rand, level) {
    const [p, base, answer] = percent(rand, level);
    return { text: `${p}% of ${base}`, answer, html: `${p}%<span class="of">of</span>${base}` };
  },
  squares(rand, level) {
    const n = int(rand, ...SQUARES[level - 1]);
    return { text: `${n} squared`, answer: n * n, html: `${n}<sup>2</sup>`, chars: String(n).length + 1 };
  },
};

/** One problem for `level` from one of `ops`, never the same text as `previous`. */
export function makeProblem(ops, level, previous = "", rand = Math.random) {
  const usable = ops.filter((op) => GENERATORS[op]);
  const list = usable.length ? usable : ["add"];
  const lv = Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, Math.round(level)));
  let problem;
  for (let tries = 0; tries < 12; tries += 1) {
    const op = pick(rand, list);
    problem = { op, level: lv, ...GENERATORS[op](rand, lv) };
    if (problem.text !== previous) break;
  }
  if (!problem.chars) problem.chars = problem.op === "percent" ? problem.text.length - 1.6 : problem.text.length;
  return problem;
}

/** A small seeded generator, so a sample month or a demo is the same every load. */
export function seeded(seed) {
  let s = 0;
  for (const ch of String(seed)) s = (s * 31 + ch.charCodeAt(0)) >>> 0;
  s = s || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 1_000_000) / 1_000_000;
  };
}
