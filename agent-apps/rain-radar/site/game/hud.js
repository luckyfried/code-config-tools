// The words and numbers around the map: the banner, the clock and wind, the next two hours, the credits.

const $ = (id) => document.getElementById(id);
const timeFormat = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

export const clockText = (ms) => timeFormat.format(new Date(ms));

export function rateText(mmPerHour, units) {
  if (units === "imperial") return `${(mmPerHour / 25.4).toFixed(2)} in/h`;
  return `${mmPerHour < 10 ? mmPerHour.toFixed(1) : Math.round(mmPerHour)} mm/h`;
}

export function windText(wind, units) {
  if (!wind || !Number.isFinite(wind.speed)) return "";
  const dir = COMPASS[Math.round(((wind.from % 360) + 360) % 360 / 45) % 8];
  const speed = units === "imperial" ? `${Math.round(wind.speed * 2.237)} mph` : `${Math.round(wind.speed * 3.6)} km/h`;
  return `Wind ${dir} ${speed}`;
}

export function relText(minutes) {
  if (Math.abs(minutes) < 1) return "Now";
  const sign = minutes < 0 ? "−" : "+";
  const m = Math.abs(Math.round(minutes));
  if (m >= 60 && m % 60 === 0) return `${sign}${m / 60} h`;
  return `${sign}${m} min`;
}

export function showPlace(name) {
  const short = name.split(",")[0];
  $("placeName").textContent = short;
  $("pinName").textContent = short;
  $("placeNow").textContent = name;
  document.title = `Rain Radar · ${short}`;
}

export function showClock(now, wind, units) {
  $("clock").textContent = clockText(now);
  $("windNow").textContent = windText(wind, units);
}

export function showBanner(look, now) {
  const banner = document.querySelector(".banner");
  const lead = $("bannerLead");
  const num = $("bannerNum");
  const unit = $("bannerUnit");
  const sub = $("bannerSub");
  banner.classList.toggle("is-dry", look?.kind === "dry");
  banner.classList.toggle("is-quiet", !look || look.kind === "none");
  if (!look || look.kind === "none") {
    lead.textContent = "Checking the radar";
    num.textContent = " ";
    unit.textContent = "";
    sub.textContent = " ";
    return;
  }
  if (look.kind === "arriving") {
    const minutes = Math.max(1, Math.round((look.at - now) / 60000));
    lead.textContent = "Rain arriving in";
    num.textContent = String(minutes);
    unit.textContent = "min";
    sub.textContent = `${look.word} from ${clockText(look.at)}`;
  } else if (look.kind === "raining") {
    lead.textContent = "Raining now";
    if (look.until) {
      num.textContent = String(Math.max(1, Math.round((look.until - now) / 60000)));
      unit.textContent = "min left";
      sub.textContent = `${look.word}, easing off by ${clockText(look.until)}`;
    } else {
      num.textContent = look.word.split(" ")[0];
      unit.textContent = "rain";
      sub.textContent = "for the next two hours";
    }
  } else {
    lead.textContent = "No rain coming";
    num.textContent = "Dry";
    unit.textContent = "";
    sub.textContent = "for the next two hours";
  }
}

// The rate at a moment, read along a line through the middles of the 15 minute steps.
function rateAt(minutely, t) {
  const pts = minutely.map((m) => [m.time + 450000, m.rate]);
  if (!pts.length) return 0;
  if (t <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) {
    if (t <= pts[i][0]) {
      const k = (t - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0]);
      return pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k;
    }
  }
  return pts[pts.length - 1][1];
}

const BARS = 12; // five minutes each

export function showStrip(source, units, now = Date.now()) {
  const minutely = Array.from({ length: BARS }, (_, i) => {
    const time = now + i * 300000;
    return source.length ? { time, rate: rateAt(source, time + 150000) } : null;
  });
  const bars = $("bars");
  if (bars.children.length !== BARS) {
    bars.replaceChildren(
      ...Array.from({ length: BARS }, () => {
        const bar = document.createElement("span");
        bar.className = "bar";
        const fill = document.createElement("span");
        fill.className = "bar-fill";
        bar.append(fill);
        return bar;
      }),
    );
  }
  let peak = null;
  [...bars.children].forEach((bar, i) => {
    const m = minutely[i];
    const rate = m ? m.rate : 0;
    bar.classList.toggle("is-mid", rate >= 1 && rate < 4);
    bar.classList.toggle("is-heavy", rate >= 4);
    bar.style.setProperty("--v", rate >= 0.1 ? Math.max(0.08, Math.min(1, Math.sqrt(rate / 5))).toFixed(3) : "0");
    bar.title = m ? `${clockText(m.time)}: ${rate >= 0.1 ? rateText(rate, units) : "dry"}` : "";
    if (m && rate >= 0.1 && (!peak || rate > peak.rate)) peak = m;
  });
  $("stripPeak").textContent = peak ? `Peak ${rateText(peak.rate, units)} at ${clockText(peak.time)}` : "Dry";
}

export function showCredits({ sample, liveRadar, liveForecast, liveMap, placeName }) {
  const parts = [];
  if (!sample) {
    if (liveRadar) parts.push("Radar RainViewer");
    if (liveForecast) parts.push("Wind and rain Open-Meteo");
    parts.push(liveMap ? "© OpenStreetMap contributors, © CARTO" : `Map drawn for ${placeName.split(",")[0]}`);
  }
  $("attribution").textContent = parts.join(" · ");
  $("attribution").hidden = parts.length === 0;
  $("sourceChip").hidden = !sample;
}

let noticeTimer = 0;
export function showNotice(text, ms = 0) {
  const el = $("notice");
  clearTimeout(noticeTimer);
  el.textContent = text || "";
  el.hidden = !text;
  if (text && ms) noticeTimer = setTimeout(() => (el.hidden = true), ms);
}

export function placePin(p, visible) {
  const pin = $("placePin");
  pin.hidden = !visible;
  pin.style.setProperty("--px", p.x.toFixed(1));
  pin.style.setProperty("--py", p.y.toFixed(1));
}
