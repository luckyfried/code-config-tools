// What the radar says about the person's own place: how wet each frame is there, and when rain arrives or stops.

const WET = 0.25; // a level above this is rain at the place

// A frame pixel's wetness: coverage, raised for the warm colors heavy cells are drawn in.
function level(r, g, b, a) {
  return (a / 255) * (1 + Math.max(0, r - b) / 255);
}

export function placeSeries(frames) {
  const size = 96;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  return frames.map((f) => {
    try {
      ctx.clearRect(0, 0, size, size);
      ctx.drawImage(f.image, 0, 0, size, size);
      const d = ctx.getImageData(size / 2 - 1, size / 2 - 1, 3, 3).data;
      let sum = 0;
      for (let i = 0; i < d.length; i += 4) sum += level(d[i], d[i + 1], d[i + 2], d[i + 3]);
      return { time: f.time, nowcast: f.nowcast, level: sum / 9 };
    } catch {
      return { time: f.time, nowcast: f.nowcast, level: 0 };
    }
  });
}

export function levelToRate(l) {
  if (l < WET) return 0;
  return l <= 1 ? 0.3 + (l - WET) * 4 : 3.3 + (l - 1) * 12;
}

export function rateWord(rate) {
  if (rate < 1) return "Light rain";
  if (rate < 4) return "Moderate rain";
  return "Heavy rain";
}

// series: per frame at the place; minutely: the next two hours in 15 minute steps. Times in ms.
export function outlook(series, minutely, now = Date.now()) {
  const past = series.filter((s) => !s.nowcast);
  const head = past[past.length - 1];
  const ahead = [head, ...series.filter((s) => s.nowcast)].filter(Boolean);
  const nowWet = (head && head.level > WET) || (minutely[0] && minutely[0].rate >= 0.2 && minutely[0].time <= now);

  if (nowWet) {
    let stop = null;
    for (let i = 1; i < ahead.length; i++) {
      if (ahead[i].level <= WET) {
        stop = cross(ahead[i - 1], ahead[i], true);
        break;
      }
    }
    if (stop === null) {
      const dry = minutely.find((m) => m.time > now && m.rate < 0.2);
      if (dry) stop = dry.time;
    }
    const rate = Math.max(levelToRate(head?.level ?? 0), minutely[0]?.rate ?? 0);
    return { kind: "raining", word: rateWord(rate), until: stop, minutes: stop ? Math.max(1, Math.round((stop - now) / 60000)) : null };
  }

  let start = null;
  for (let i = 1; i < ahead.length; i++) {
    if (ahead[i].level > WET) {
      start = cross(ahead[i - 1], ahead[i], false);
      break;
    }
  }
  if (start === null) {
    const wet = minutely.find((m) => m.rate >= 0.2);
    if (wet) start = Math.max(wet.time, now + 60000);
  }
  if (start === null) return { kind: "dry" };
  const later = minutely.filter((m) => m.time >= start - 15 * 60000 && m.time < start + 60 * 60000);
  const peakRate = Math.max(0, ...later.map((m) => m.rate), ...ahead.map((s) => levelToRate(s.level)));
  return { kind: "arriving", at: start, minutes: Math.max(1, Math.round((start - now) / 60000)), word: rateWord(peakRate) };
}

// The time the level passes the wet line between two frames, read off a straight line between them.
function cross(a, b, falling) {
  const da = a.level - WET;
  const db = b.level - WET;
  if (falling ? da <= 0 : db <= 0) return b.time;
  const t = da / (da - db);
  return a.time + Math.max(0, Math.min(1, t)) * (b.time - a.time);
}
