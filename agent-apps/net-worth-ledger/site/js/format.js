// Money and month words in the browser's locale and the ledger's currency.
const LOCALE = (navigator.languages && navigator.languages[0]) || navigator.language || "en-US";

function currencyFormat(currency, options) {
  try {
    return new Intl.NumberFormat(LOCALE, { style: "currency", currency, ...options });
  } catch {
    return new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD", ...options });
  }
}

/** A true minus sign, set tight against the figure, in place of the hyphen Intl writes. */
const minus = (text) => text.replace(/-/g, "\u2212");

export function makeFormat(currency) {
  const whole = currencyFormat(currency, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const signed = currencyFormat(currency, { minimumFractionDigits: 0, maximumFractionDigits: 0, signDisplay: "exceptZero" });
  const compact = currencyFormat(currency, { notation: "compact", minimumFractionDigits: 0, maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 0 });
  const monthLong = new Intl.DateTimeFormat(LOCALE, { month: "long", year: "numeric", timeZone: "UTC" });
  const monthOnly = new Intl.DateTimeFormat(LOCALE, { month: "long", timeZone: "UTC" });
  const monthShort = new Intl.DateTimeFormat(LOCALE, { month: "short", timeZone: "UTC" });
  const monthShortYear = new Intl.DateTimeFormat(LOCALE, { month: "short", year: "numeric", timeZone: "UTC" });
  const year = new Intl.DateTimeFormat(LOCALE, { year: "numeric", timeZone: "UTC" });
  const date = (index) => Date.UTC(Math.floor(index / 12), index % 12, 1);
  return {
    money: (value) => minus(whole.format(Math.round(value))),
    signed: (value) => minus(signed.format(Math.round(value))),
    compact: (value) => minus(compact.format(value)),
    percent: (value) => percent.format(value),
    monthLong: (index) => monthLong.format(date(index)),
    monthOnly: (index) => monthOnly.format(date(index)),
    monthShort: (index) => monthShort.format(date(index)),
    monthShortYear: (index) => monthShortYear.format(date(index)),
    year: (index) => year.format(date(index)),
  };
}
