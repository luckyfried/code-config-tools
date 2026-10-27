// Money in the export's currency, whole units on the map and cents in the table.
const cache = new Map();

function formatter(currency, cents) {
  const key = `${currency}:${cents}`;
  if (!cache.has(key)) {
    cache.set(key, new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: cents ? 2 : 0,
      minimumFractionDigits: cents ? 2 : 0,
    }));
  }
  return cache.get(key);
}

export const money = (currency, cents) => formatter(currency, false).format(Math.round(cents / 100));
export const exact = (currency, cents) => formatter(currency, true).format(cents / 100);
export const percent = (part, whole) => (whole > 0 ? `${Math.round((part / whole) * 100)}%` : "0%");

export function clip(text, max) {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}
