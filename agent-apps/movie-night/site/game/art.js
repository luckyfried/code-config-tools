// A poster for every film: the file the inputs named, else Wikipedia's lead image when the household turned lookups on,
// else a typeset card drawn here, the title in big type on a color that comes from the title itself.

const CARD_W = 640;
const CARD_H = 960;
const cards = new Map();
const cardUrls = new Map();

export function hashOf(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function seeded(seed) {
  let a = seed || 1;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function fontsReady() {
  const loads = [document.fonts.load('800 120px "Bricolage"'), document.fonts.load('600 32px "Bricolage"')];
  return Promise.race([Promise.all(loads), new Promise((r) => setTimeout(r, 900))]).catch(() => {});
}

function wrap(g, words, width) {
  const lines = [];
  let line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (g.measureText(next).width <= width || !line) line = next;
    else {
      lines.push(line);
      line = w;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export function drawCard(film) {
  if (cards.has(film.key)) return cards.get(film.key);
  const c = document.createElement("canvas");
  c.width = CARD_W;
  c.height = CARD_H;
  const g = c.getContext("2d");
  const h = hashOf(`${film.title}|${film.year ?? ""}`);
  const rand = seeded(h);
  const hue = h % 360;
  const glowHue = (hue + 26 + ((h >>> 12) % 40)) % 360;
  const variant = (h >>> 8) % 4;

  const ground = g.createLinearGradient(0, 0, 0, CARD_H);
  ground.addColorStop(0, `hsl(${hue} 46% 24%)`);
  ground.addColorStop(1, `hsl(${(hue + 14) % 360} 52% 10%)`);
  g.fillStyle = ground;
  g.fillRect(0, 0, CARD_W, CARD_H);

  const glow = `hsl(${glowHue} 82% 63%)`;
  const glowDeep = `hsl(${glowHue} 70% 42%)`;
  g.save();
  if (variant === 0) {
    const sun = g.createLinearGradient(0, 120, 0, 560);
    sun.addColorStop(0, glow);
    sun.addColorStop(1, glowDeep);
    g.fillStyle = sun;
    g.beginPath();
    g.arc(410, 360, 220, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = ground;
    for (let i = 0; i < 7; i += 1) g.fillRect(150, 380 + i * 30, 520, 6 + i * 2.4);
  } else if (variant === 1) {
    g.lineWidth = 14;
    for (let i = 0; i < 9; i += 1) {
      g.strokeStyle = `hsl(${glowHue} 80% ${66 - i * 4}% / ${0.95 - i * 0.09})`;
      g.beginPath();
      g.arc(320, 360, 40 + i * 34, 0, Math.PI * 2);
      g.stroke();
    }
  } else if (variant === 2) {
    g.translate(CARD_W / 2, 330);
    g.rotate(-0.42);
    for (let i = 0; i < 4; i += 1) {
      g.fillStyle = `hsl(${(glowHue + i * 14) % 360} 78% ${64 - i * 8}%)`;
      g.fillRect(-520, -150 + i * 78, 1040, 54);
    }
  } else {
    const dome = g.createLinearGradient(0, 110, 0, 600);
    dome.addColorStop(0, glow);
    dome.addColorStop(1, `hsl(${glowHue} 60% 30% / 0.2)`);
    g.fillStyle = dome;
    g.beginPath();
    g.moveTo(170, 600);
    g.lineTo(170, 290);
    g.arc(320, 290, 150, Math.PI, 0);
    g.lineTo(470, 600);
    g.closePath();
    g.fill();
    g.fillStyle = `hsl(${hue} 40% 92%)`;
    g.beginPath();
    g.arc(320 + (rand() - 0.5) * 120, 250 + rand() * 80, 26, 0, Math.PI * 2);
    g.fill();
  }
  g.restore();

  const shade = g.createLinearGradient(0, 480, 0, CARD_H);
  shade.addColorStop(0, "rgba(0,0,0,0)");
  shade.addColorStop(1, "rgba(0,0,0,0.55)");
  g.fillStyle = shade;
  g.fillRect(0, 480, CARD_W, CARD_H - 480);

  for (let i = 0; i < 2600; i += 1) {
    g.fillStyle = rand() > 0.5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.07)";
    g.fillRect(rand() * CARD_W, rand() * CARD_H, 2, 2);
  }

  const ink = `hsl(${hue} 70% 95%)`;
  g.fillStyle = ink;
  g.textBaseline = "alphabetic";
  g.font = '600 30px "Bricolage", sans-serif';
  g.letterSpacing = "6px";
  g.fillText(film.year ? String(film.year) : "ON THE LIST", 56, 96);
  g.fillRect(56, 116, 64, 4);
  g.letterSpacing = "0px";

  const words = film.title.split(/\s+/);
  let size = 156;
  let lines = [];
  g.fontStretch = "condensed";
  for (; size >= 56; size -= 6) {
    g.font = `800 ${size}px "Bricolage", sans-serif`;
    lines = wrap(g, words, CARD_W - 112);
    const widest = Math.max(...lines.map((l) => g.measureText(l).width));
    if (lines.length <= 4 && widest <= CARD_W - 112) break;
  }
  const lead = size * 0.9;
  let y = CARD_H - 70 - (lines.length - 1) * lead;
  for (const l of lines) {
    g.fillText(l, 54, y);
    y += lead;
  }
  g.fontStretch = "normal";
  cards.set(film.key, c);
  return c;
}

export function cardUrl(film) {
  if (!cardUrls.has(film.key)) cardUrls.set(film.key, drawCard(film).toDataURL("image/jpeg", 0.86));
  return cardUrls.get(film.key);
}

function loadImage(url, cross) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    if (cross) img.crossOrigin = "anonymous";
    img.decoding = "async";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(url));
    img.src = url;
  });
}

// One query to the Wikipedia action API per candidate page name; the first film page with a lead image wins.
async function wikipediaImage(film) {
  const names = film.year ? [`${film.title} (${film.year} film)`, `${film.title} (film)`, film.title] : [`${film.title} (film)`, film.title];
  for (const name of names) {
    const q = new URLSearchParams({
      action: "query",
      format: "json",
      formatversion: "2",
      origin: "*",
      redirects: "1",
      prop: "pageimages|description",
      piprop: "thumbnail",
      pithumbsize: "640",
      titles: name,
    });
    const res = await fetch(`https://en.wikipedia.org/w/api.php?${q}`, {
      headers: { "Api-User-Agent": "MovieNight/1.0 (a household watch list page)" },
    });
    if (!res.ok) continue;
    const page = (await res.json()).query?.pages?.[0];
    const src = page?.thumbnail?.source;
    if (src && /film|movie/i.test(page.description || "")) return src;
  }
  return null;
}

// Resolves to { source, url, kind } where source is an image or a canvas the scene can draw.
export async function artFor(film, lookup) {
  if (film.poster) {
    try {
      const img = await loadImage(film.poster, false);
      return { source: img, url: film.poster, kind: "file" };
    } catch {
      // A poster that will not load falls through to the card.
    }
  }
  if (lookup) {
    try {
      const url = await wikipediaImage(film);
      if (url) {
        const img = await loadImage(url, true);
        return { source: img, url, kind: "lookup" };
      }
    } catch {
      // No lookup answer: the card stands in.
    }
  }
  return { source: drawCard(film), url: null, kind: "card" };
}

export function urlFor(film, art) {
  return art?.url || cardUrl(film);
}
