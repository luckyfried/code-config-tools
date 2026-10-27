// The opening: the names arrive letter by letter while scattered digits fly in, cycle, and settle into the date.
const EASE = "cubic-bezier(0.23, 1, 0.32, 1)";

export function playHero(stage) {
  const box = stage.getBoundingClientRect();
  let seed = 97;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;

  stage.querySelectorAll(".ch").forEach((el, i) => {
    el.animate(
      [{ opacity: 0, transform: "translate3d(0, 0.42em, 0) rotate(5deg)" }, { opacity: 1, transform: "none" }],
      { duration: 820, delay: 80 + i * 42, easing: EASE, fill: "both" },
    );
  });
  stage.querySelectorAll(".names__amp, .date__rule").forEach((el, i) => {
    el.animate([{ opacity: 0, scale: "0.6" }, { opacity: 1, scale: "1" }],
      { duration: 700, delay: 380 + i * 90, easing: EASE, fill: "both" });
  });
  const rise = [...stage.querySelectorAll(".hero__line, .hero__when, .countdown__unit")];
  rise.forEach((el, i) => {
    el.animate([{ opacity: 0, translate: "0 14px" }, { opacity: 1, translate: "0 0" }],
      { duration: 700, delay: i === 0 ? 60 : 950 + i * 70, easing: EASE, fill: "both" });
  });

  const digits = [...stage.querySelectorAll(".date__digit")];
  digits.forEach((el, i) => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2 - box.left;
    const cy = r.top + r.height / 2 - box.top;
    const tx = (0.08 + rand() * 0.84) * box.width - cx;
    const ty = (0.1 + rand() * 0.8) * box.height - cy;
    const turn = (rand() - 0.5) * 70;
    const scale = 1.6 + rand() * 2.2;
    const delay = 140 + i * 34;
    const duration = 880 + i * 30;
    el.animate(
      [
        { opacity: 0, transform: `translate3d(${tx}px, ${ty}px, 0) rotate(${turn}deg) scale(${scale})` },
        { opacity: 0.85, offset: 0.2 },
        { opacity: 1, transform: "none" },
      ],
      { duration, delay, easing: "cubic-bezier(0.16, 0.8, 0.12, 1)", fill: "both" },
    );
    const final = el.textContent;
    const spin = setInterval(() => { el.textContent = String(Math.floor(rand() * 10)); }, 60);
    setTimeout(() => { clearInterval(spin); el.textContent = final; }, delay + duration * 0.72);
  });

  const ghosts = [];
  for (let i = 0; i < 22; i++) {
    const g = document.createElement("span");
    g.className = "ghost";
    g.setAttribute("aria-hidden", "true");
    g.textContent = String(Math.floor(rand() * 10));
    g.style.setProperty("--gx", (4 + rand() * 88).toFixed(1));
    g.style.setProperty("--gy", (6 + rand() * 82).toFixed(1));
    g.style.setProperty("--gs", (2 + rand() * 7).toFixed(1));
    stage.prepend(g);
    ghosts.push(g);
    const dx = (50 - parseFloat(g.style.getPropertyValue("--gx"))) * box.width * 0.004;
    const dy = (46 - parseFloat(g.style.getPropertyValue("--gy"))) * box.height * 0.004;
    g.animate(
      [
        { opacity: 0, transform: "translate3d(0, 0, 0) scale(1)" },
        { opacity: 0.22, offset: 0.35 },
        { opacity: 0, transform: `translate3d(${dx}px, ${dy}px, 0) scale(0.4)` },
      ],
      { duration: 1500 + rand() * 300, delay: rand() * 220, easing: EASE, fill: "both" },
    );
  }
  setTimeout(() => ghosts.forEach((g) => g.remove()), 2300);
}
