// The heads-up layer: the pearl count, the time of day on the glass, the first-visit hint, toasts, and the pearls
// that fly from the sand to the counter.
const $ = (id) => document.getElementById(id);

export function createHud({ reducedMotion }) {
  const count = $("pearlCount");
  const pearls = $("pearls");
  const shopPearls = $("shopPearls");
  const dayLabel = $("daylabel");
  const hint = $("hint");
  const toasts = $("toasts");
  const flyers = $("flyers");
  let shown = -1;
  let target = 0;
  let bumpTimer = 0;
  const fmt = new Intl.NumberFormat("en-US");

  function setPearls(n, animate) {
    target = n;
    if (!animate || shown < 0) {
      shown = n;
      count.textContent = fmt.format(n);
      shopPearls.textContent = fmt.format(n);
    }
  }

  // the counter rolls toward its target a step at a time, so a sweep of many pearls ticks up visibly
  function tick(dt) {
    if (shown === target) return;
    const gap = target - shown;
    const step = Math.sign(gap) * Math.max(1, Math.ceil(Math.abs(gap) * Math.min(1, dt * 8)));
    shown = Math.abs(step) >= Math.abs(gap) ? target : shown + step;
    count.textContent = fmt.format(shown);
    shopPearls.textContent = fmt.format(shown);
    if (performance.now() - bumpTimer > 260) {
      bumpTimer = performance.now();
      pearls.classList.remove("is-bump");
      void pearls.offsetWidth;
      pearls.classList.add("is-bump");
    }
  }

  function setDay(label, night) {
    if (dayLabel.textContent !== label) dayLabel.textContent = label;
    document.body.classList.toggle("is-night", night);
  }

  function hideHint() {
    hint.classList.add("is-gone");
  }

  function setHint(text) {
    hint.textContent = text;
    hint.classList.remove("is-gone");
  }

  function toast(text) {
    const el = document.createElement("p");
    el.className = "toast";
    el.textContent = text;
    toasts.append(el);
    while (toasts.children.length > 3) toasts.firstElementChild.remove();
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 450);
    }, 2600);
  }

  // a pearl leaves the sand at (x, y) on screen and lands in the counter; done() runs when it arrives
  function fly(x, y, done) {
    const to = pearls.querySelector(".pearl-dot").getBoundingClientRect();
    const tx = to.left + to.width / 2, ty = to.top + to.height / 2;
    if (reducedMotion) {
      done();
      return;
    }
    const el = document.createElement("span");
    el.className = "pearl-dot flyer";
    flyers.append(el);
    const mx = (x + tx) / 2 + (Math.random() - 0.5) * 120, my = Math.min(y, ty) - 90 - Math.random() * 80;
    const anim = el.animate([
      { transform: `translate(${x}px, ${y}px) scale(0.6)`, opacity: 0 },
      { transform: `translate(${x}px, ${y - 24}px) scale(1.15)`, opacity: 1, offset: 0.18 },
      { transform: `translate(${mx}px, ${my}px) scale(1)`, opacity: 1, offset: 0.55 },
      { transform: `translate(${tx}px, ${ty}px) scale(0.7)`, opacity: 0.9 },
    ], { duration: 900 + Math.random() * 250, easing: "cubic-bezier(0.45, 0, 0.25, 1)" });
    anim.onfinish = () => {
      el.remove();
      done();
    };
  }

  return { setPearls, tick, setDay, hideHint, setHint, toast, fly };
}
