// Numbers and dates in the words and units a runner reads.

export const UNIT_M = { km: 1000, mi: 1609.344 };

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const SPORT_WORD = { run: "run", ride: "ride", walk: "walk", hike: "hike" };

export function distance(meters, units, digits) {
  const value = meters / UNIT_M[units];
  const places = digits ?? (value < 100 ? 1 : 0);
  return value.toLocaleString("en-US", { minimumFractionDigits: places, maximumFractionDigits: places });
}

export function clock(seconds) {
  if (seconds == null) return "";
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}` : `${m}:${String(r).padStart(2, "0")}`;
}

// A ride reads as speed; everything on foot reads as pace.
export function pace(meters, seconds, units, sport) {
  if (!seconds || !meters) return { value: "", unit: "" };
  if (sport === "ride") {
    const perHour = (meters / UNIT_M[units]) / (seconds / 3600);
    return { value: perHour.toFixed(1), unit: units === "km" ? "km/h" : "mph" };
  }
  const per = seconds / (meters / UNIT_M[units]);
  return { value: clock(per), unit: `/${units}` };
}

export function paceOnly(meters, seconds, units, sport) {
  const p = pace(meters, seconds, units, sport);
  return p.value;
}

export function climb(meters, units) {
  if (units === "mi") return { value: Math.round(meters * 3.28084).toLocaleString("en-US"), unit: "ft" };
  return { value: Math.round(meters).toLocaleString("en-US"), unit: "m" };
}

function parts(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d, wd: new Date(Date.UTC(y, m - 1, d)).getUTCDay() };
}

export function shortDate(iso) {
  if (!iso) return "No date";
  const { y, m, d } = parts(iso);
  return `${MONTHS_SHORT[m - 1]} ${d}, ${y}`;
}

export function tileDate(iso) {
  if (!iso) return "";
  const { m, d } = parts(iso);
  return `${MONTHS_SHORT[m - 1]} ${d}`;
}

export function longDate(iso, time) {
  if (!iso) return "No date recorded";
  const { y, m, d, wd } = parts(iso);
  const day = `${DAYS[wd]}, ${MONTHS_LONG[m - 1]} ${d}, ${y}`;
  if (!time) return day;
  const [hh, mm] = time.split(":").map(Number);
  const h12 = ((hh + 11) % 12) + 1;
  return `${day} at ${h12}:${String(mm).padStart(2, "0")} ${hh < 12 ? "am" : "pm"}`;
}

export const monthShort = (index) => MONTHS_SHORT[index];
export const monthLong = (index) => MONTHS_LONG[index];
export const monthLetter = (index) => MONTHS_SHORT[index][0];

export function sportWord(sport, count) {
  const word = SPORT_WORD[sport] ?? "activity";
  return count === 1 ? word : `${word}s`;
}

export function hours(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h} h ${m} min` : `${m} min`;
}

export function count(n) {
  return n.toLocaleString("en-US");
}
