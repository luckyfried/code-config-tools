// Words and numbers as the person reads them, through Intl, in the units they chose.

import { dateOfDay } from "./trend.js";
import { fromKg } from "./store.js";

const UNIT = { kg: "kilogram", lb: "pound" };
const cache = new Map();

function numberFormat(units, digits, withUnit) {
  const key = `${units}|${digits}|${withUnit}`;
  if (!cache.has(key)) {
    cache.set(
      key,
      new Intl.NumberFormat(undefined, {
        ...(withUnit ? { style: "unit", unit: UNIT[units], unitDisplay: "short" } : {}),
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }),
    );
  }
  return cache.get(key);
}

export function weight(kg, units, { unit = true, digits = 1 } = {}) {
  return numberFormat(units, digits, unit).format(fromKg(kg, units));
}

export function plain(value, digits = 1) {
  return numberFormat("kg", digits, false).format(value);
}

// A change with its sign, written with a true minus.
export function change(kg, units) {
  const v = fromKg(kg, units);
  const text = numberFormat(units, 1, true).format(Math.abs(v));
  if (Math.abs(v) < 0.05) return text;
  return `${v < 0 ? "−" : "+"}${text}`;
}

const dayFormats = {
  short: new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }),
  long: new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }),
  row: new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }),
  month: new Intl.DateTimeFormat(undefined, { month: "short" }),
  monthYear: new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric" }),
  year: new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }),
};

export function day(dayNumber, style = "short") {
  return dayFormats[style].format(dateOfDay(dayNumber));
}

export function inDays(n) {
  if (n <= 1) return "tomorrow";
  if (n < 14) return `in ${n} days`;
  if (n < 70) return `in ${Math.round(n / 7)} weeks`;
  return `in ${Math.round(n / 30.44)} months`;
}
