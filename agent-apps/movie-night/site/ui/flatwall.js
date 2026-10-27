// The wall without WebGL. "css3d" is a CSS 3D coverflow driven by the same glide and springs as the scene; "grid" is
// the reduced-motion wall, every poster at once, fading in, the lit one ringed.
import { slot, spring } from "../game/motion.js";

export class FlatWall {
  constructor(el, mode, onTap) {
    this.el = el;
    this.mode = mode;
    this.onTap = onTap;
    el.hidden = false;
    el.classList.toggle("is-grid", mode === "grid");
    el.replaceChildren();
    this.track = document.createElement("div");
    this.track.className = "flat-track";
    this.beam = document.createElement("div");
    this.beam.className = "flat-spot";
    this.track.append(this.beam);
    el.append(this.track);
    this.items = [];
    this.shift = { x: 0, v: 0 };
    this.goalShift = 0;
    this.resize();
  }

  resize() {
    const phone = innerWidth < 900;
    this.phone = phone;
    const w = phone ? Math.min(innerWidth * 0.62, innerHeight * 0.3) : Math.min(innerHeight * 0.33, 320);
    this.unit = w / 1.4;
    this.el.style.setProperty("--poster-w", `${Math.round(w)}px`);
  }

  setCover(right) {
    this.goalShift = -right / 2;
  }

  setFilms(films, urls) {
    for (const it of this.items) it.el.remove();
    this.items = films.map((film, i) => {
      const el = document.createElement("button");
      el.type = "button";
      el.className = "flat-poster";
      el.setAttribute("aria-label", `${film.title}${film.year ? `, ${film.year}` : ""}`);
      const img = document.createElement("img");
      img.alt = "";
      img.width = 400;
      img.height = 600;
      img.decoding = "async";
      img.src = urls[i];
      el.append(img);
      el.dataset.index = String(i);
      // The coverflow takes pointer taps through the wall's own input; a click here is a key press, or a tap on the grid.
      el.addEventListener("click", (e) => {
        if (this.mode === "grid" || e.detail === 0) this.onTap(i);
      });
      this.track.append(el);
      if (this.mode === "grid") requestAnimationFrame(() => el.classList.add("is-shown"));
      return { el, img, rot: { x: 0, v: 0 }, placed: false };
    });
  }

  setUrl(i, url) {
    const it = this.items[i];
    if (it) it.img.src = url;
  }

  update(dt, p, spot) {
    if (this.mode === "grid") {
      this.items.forEach((it, i) => it.el.classList.toggle("is-spot", i === spot.index && spot.drop > 0.5));
      return;
    }
    spring(this.shift, this.goalShift, 70, 0.92, dt);
    this.track.style.setProperty("--shift", `${this.shift.x.toFixed(1)}px`);
    const u = this.unit;
    this.items.forEach((it, i) => {
      const d = i - p;
      const s = slot(d, this.phone);
      if (!it.placed) {
        it.rot.x = s.rot;
        it.placed = true;
      }
      spring(it.rot, s.rot, 190, 0.5, dt);
      const st = it.el.style;
      st.setProperty("--tx", `${(s.x * u).toFixed(1)}px`);
      st.setProperty("--tz", `${((s.z - 0.5) * u).toFixed(1)}px`);
      st.setProperty("--ry", `${it.rot.x.toFixed(3)}rad`);
      st.setProperty("--zi", String(100 - Math.round(Math.abs(d) * 10)));
      it.el.classList.toggle("is-hidden", Math.abs(d) > 6);
      it.el.classList.toggle("is-dim", i !== spot.index && spot.dimming > 0.5);
    });
    const at = this.items[spot.index] ? slot(spot.index - p, this.phone).x * u : 0;
    this.beam.style.setProperty("--tx", `${at.toFixed(1)}px`);
    this.beam.classList.toggle("is-on", spot.drop > 0.5);
  }
}
