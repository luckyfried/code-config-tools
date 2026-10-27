// Starts the page: the opening, the countdown, the wind layer, the scroll motion, the map, and the reply form.
import { createSky } from "../scene/particles.js";
import { playHero } from "./hero.js";
import { startCountdown } from "./countdown.js";
import { createScroll, glide } from "./scroll.js";
import { drawMap, placePin } from "./map.js";
import { setUpReply } from "./rsvp.js";
import { setUpSheet } from "./sheet.js";
import { load, save } from "./state.js";

const config = window.__APP_CONFIG__;
const doc = document;
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
const stage = doc.querySelector("[data-stage]");

if (!calm && stage) playHero(stage);
const countdown = doc.querySelector("[data-countdown]");
if (countdown) startCountdown(countdown, new Date(config.date).getTime(), { animate: !calm });

const mapBox = doc.querySelector("[data-map]");
let venue = null;
if (mapBox && config.place && typeof config.place.lat === "number") {
  venue = drawMap(mapBox.querySelector("[data-map-svg]"), config.place).venue;
  placePin(mapBox, venue);
}

const android = /Android/i.test(navigator.userAgent);
doc.querySelector('[data-maps="geo"]')?.toggleAttribute("hidden", !android);
doc.querySelector('[data-maps="apple"]')?.toggleAttribute("hidden", android);

setUpReply(doc, config);
setUpSheet(doc);

const seen = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    e.target.classList.add("is-in");
    seen.unobserve(e.target);
  }
}, { threshold: 0.2 });
doc.querySelectorAll("[data-photo]").forEach((el) => seen.observe(el));
if (mapBox) seen.observe(mapBox);

const scroll = createScroll(doc);
const sky = calm ? null : createSky(doc.querySelector("[data-sky]"), config.kind);

let lastY = -1;
let lastT = 0;
let velocity = 0;
const loop = (now) => {
  const y = window.scrollY;
  const dt = lastT ? Math.max(1, now - lastT) : 16;
  velocity = velocity * 0.85 + ((y - (lastY < 0 ? y : lastY)) / dt) * 1000 * 0.15;
  lastT = now;
  if (y !== lastY) {
    scroll.update(y);
    lastY = y;
  }
  if (sky) {
    const m = scroll.metrics();
    const end = m ? m.hero : 1;
    const density = 1 - 0.6 * Math.min(1, Math.max(0, (y - end * 0.45) / (end * 0.55)));
    sky.frame(now, y, velocity, density);
  }
  requestAnimationFrame(loop);
};

const remeasure = () => {
  scroll.measure();
  scroll.update(window.scrollY);
  sky?.resize();
  if (venue) placePin(mapBox, venue);
};
window.addEventListener("resize", remeasure);
window.addEventListener("load", remeasure);
doc.fonts?.ready.then(remeasure);
requestAnimationFrame(loop);

// The opening glide runs once per visitor, after the date has settled, on a page opened at its top.
const fresh = !calm && !location.hash && window.scrollY < 4 && !load().toured;
if (fresh) {
  setTimeout(() => {
    if (window.scrollY > 4) return;
    scroll.measure();
    const m = scroll.metrics();
    const vh = m.vh;
    const wanted = [{ y: m.hero - vh * 0.08, ms: 1150, hold: 300 }];
    const last = m.photos[m.photos.length - 1];
    if (last) wanted.push({ y: last.top + last.h * 0.5 - vh * 0.55, ms: 950, hold: 250 });
    if (m.body) wanted.push({ y: m.body.top + m.body.h * 0.6 - vh * 0.62, ms: 1000, hold: 300 });
    if (m.map) wanted.push({ y: m.map.top - (vh - m.map.h) / 2, ms: 1150 });
    const points = wanted.filter((p, i) => i === 0 || p.y > wanted[i - 1].y + 40);
    glide(points, { onEnd: () => save({ toured: true }) });
  }, 2500);
}
