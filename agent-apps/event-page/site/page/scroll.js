// Scroll-driven motion: the pinned hero's progress, photo parallax, the schedule's ink, and the map's tilt, all read
// from offsets measured once per resize, so a frame does arithmetic and writes, never layout reads.
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (t) => t * t * (3 - 2 * t);

export function createScroll(doc) {
  const hero = doc.querySelector("[data-hero]");
  const stage = doc.querySelector("[data-stage]");
  const bar = doc.querySelector("[data-bar]");
  const photos = [...doc.querySelectorAll("[data-photo]")].map((el) => ({ el, img: el.querySelector("img") }));
  const body = doc.querySelector(".schedule__body");
  const stops = [...doc.querySelectorAll(".schedule .stop")];
  const wrap = doc.querySelector("[data-map-wrap]");
  const map = doc.querySelector("[data-map]");
  let m = null;

  const top = (el) => el.getBoundingClientRect().top + window.scrollY;
  const measure = () => {
    m = {
      vh: window.innerHeight,
      hero: hero ? hero.offsetHeight : 0,
      photos: photos.map((p) => ({ top: top(p.el), h: p.el.offsetHeight })),
      body: body ? { top: top(body), h: body.offsetHeight } : null,
      stops: body ? stops.map((s) => top(s) + 24) : [],
      map: wrap ? { top: top(wrap), h: wrap.offsetHeight } : null,
    };
  };

  let lit = -1;
  const update = (y) => {
    if (!m) measure();
    const { vh } = m;
    const span = Math.max(1, m.hero - vh);
    stage?.style.setProperty("--hp", clamp(y / span).toFixed(4));
    bar?.classList.toggle("is-solid", y > span - 10);

    photos.forEach((p, i) => {
      const r = m.photos[i];
      if (y + vh < r.top - 40 || y > r.top + r.h + 40) return;
      const t = clamp((y + vh - r.top) / (vh + r.h));
      p.img.style.transform = `translate3d(0, ${((0.5 - t) * 13).toFixed(2)}%, 0) scale(1.16)`;
    });

    if (m.body) {
      const ink = clamp((y + vh * 0.62 - m.body.top) / m.body.h);
      body.style.setProperty("--ink", ink.toFixed(4));
      const reach = m.body.top + ink * m.body.h;
      let n = -1;
      m.stops.forEach((s, i) => { if (s <= reach + 2) n = i; });
      if (n !== lit) {
        stops.forEach((s, i) => s.classList.toggle("is-lit", i <= n));
        lit = n;
      }
    }

    if (m.map && map) {
      const t = smooth(clamp((y + vh - m.map.top) / (vh * 0.85 + m.map.h * 0.35)));
      const tilt = 1 - t;
      map.style.transform = `rotateX(${(8 + tilt * 50).toFixed(2)}deg) translate3d(0, ${(tilt * 60).toFixed(1)}px, 0)`
        + ` scale(${(1 - tilt * 0.08).toFixed(4)})`;
    }
  };

  return { measure, update, metrics: () => m };
}

// The opening glide: once per visitor, the page eases down through the story, the schedule, and the map, then
// rests. Any wheel, touch, click, or key hands the page back at once.
export function glide(points, { onEnd }) {
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    for (const type of events) window.removeEventListener(type, stop, opts);
    onEnd();
  };
  const events = ["wheel", "touchstart", "pointerdown", "keydown"];
  const opts = { passive: true, capture: true };
  for (const type of events) window.addEventListener(type, stop, opts);

  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  let i = 0;
  let from = window.scrollY;
  let start = performance.now();
  const step = (now) => {
    if (stopped) return;
    const leg = points[i];
    const t = clamp((now - start) / leg.ms);
    window.scrollTo(0, from + (leg.y - from) * ease(t));
    if (t < 1) return requestAnimationFrame(step);
    i++;
    if (i >= points.length) return stop();
    const wait = leg.hold || 0;
    setTimeout(() => {
      from = window.scrollY;
      start = performance.now();
      requestAnimationFrame(step);
    }, wait);
  };
  requestAnimationFrame(step);
  return stop;
}
