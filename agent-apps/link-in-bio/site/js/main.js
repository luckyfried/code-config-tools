// Brings the profile card to life: the name settles in, the stage drifts, the card tilts, the QR code draws,
// a long press copies a link, and Share hands the page's address to the phone's share sheet or copies it.
import { startMesh } from "./mesh.js";
import { startTilt, startMagnetic } from "./tilt.js";
import { drawQR } from "./qr.js";

const config = window.__APP_CONFIG__ || {};
const root = document.documentElement;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

function splitName() {
  const h1 = document.querySelector(".name");
  if (!h1) return;
  const text = h1.textContent.trim();
  const segment = (word) => ("Segmenter" in Intl
    ? Array.from(new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(word), (s) => s.segment)
    : Array.from(word));
  h1.setAttribute("aria-label", text);
  h1.textContent = "";
  let i = 0;
  text.split(/(\s+)/).forEach((part) => {
    if (!part) return;
    if (/^\s+$/.test(part)) {
      h1.append(" ");
      return;
    }
    const word = document.createElement("span");
    word.className = "word";
    word.setAttribute("aria-hidden", "true");
    segment(part).forEach((ch) => {
      const span = document.createElement("span");
      span.className = "ch";
      span.textContent = ch;
      span.style.setProperty("--i", String(i));
      i += 1;
      word.append(span);
    });
    h1.append(word);
  });
  h1.classList.add("is-split");
}

const toast = document.querySelector(".toast");
let toastTimer = 0;
function say(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-shown");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-shown"), 1800);
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.className = "visually-hidden";
    document.body.append(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    area.remove();
    return ok;
  }
}

async function copyAndSay(text, done) {
  say((await copy(text)) ? done : "This browser blocked copying the link.");
}

function wireCopy() {
  document.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-share]");
    if (!button) return;
    const url = button.dataset.share;
    if (navigator.share && matchMedia("(pointer: coarse)").matches) {
      try {
        await navigator.share({ title: document.title, url });
        return;
      } catch (err) {
        if (err && err.name === "AbortError") return;
      }
    }
    copyAndSay(url, "Page link copied");
  });

  document.querySelectorAll(".link__main").forEach((a) => {
    const row = a.closest(".link");
    let timer = 0;
    let fired = false;
    let origin = null;
    const clear = () => {
      clearTimeout(timer);
      timer = 0;
      row.classList.remove("is-pressing");
    };
    a.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "touch") return;
      fired = false;
      origin = [e.clientX, e.clientY];
      row.classList.add("is-pressing");
      timer = setTimeout(() => {
        fired = true;
        clear();
        if (navigator.vibrate) navigator.vibrate(12);
        copyAndSay(a.href, "Link copied");
      }, 520);
    });
    a.addEventListener("pointermove", (e) => {
      if (timer && origin && Math.hypot(e.clientX - origin[0], e.clientY - origin[1]) > 10) clear();
    });
    a.addEventListener("pointerup", clear);
    a.addEventListener("pointercancel", clear);
    a.addEventListener("contextmenu", (e) => { if (fired || timer) e.preventDefault(); });
    a.addEventListener("click", (e) => {
      if (fired) {
        e.preventDefault();
        fired = false;
      }
    });
  });
}

splitName();
wireCopy();

const live = startMesh(document.querySelector(".mesh"), { still: reduce });
if (!live) root.classList.add("no-gl");

const card = document.querySelector(".card");
if (card && live && !reduce) startTilt(card, [card.querySelector(".card__sheen"), card.querySelector(".card__rim")]);
if (!reduce) startMagnetic(document.querySelectorAll(".link"));

const qrCanvas = document.querySelector(".qr__canvas");
if (qrCanvas && config.url) {
  if (reduce) drawQR(qrCanvas, config.url, { animate: false });
  else setTimeout(() => drawQR(qrCanvas, config.url, { animate: true }), 360);
}
