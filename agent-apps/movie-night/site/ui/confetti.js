// Confetti for the pick: paper pieces thrown up from a point, falling with drag and flutter, gone in about three seconds.

export class Confetti {
  constructor(canvas) {
    this.canvas = canvas;
    this.g = canvas.getContext("2d");
    this.parts = [];
    this.colors = ["gold"];
    this.raf = 0;
    this.last = 0;
    this.resize();
  }

  setColors(list) {
    this.colors = list.filter(Boolean);
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.dpr = dpr;
    this.canvas.width = Math.round(innerWidth * dpr);
    this.canvas.height = Math.round(innerHeight * dpr);
  }

  burst(x, y, count = 150) {
    for (let i = 0; i < count; i += 1) {
      const a = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 0.95;
      const v = 380 + Math.random() * 620;
      this.parts.push({
        x,
        y,
        vx: Math.cos(a) * v,
        vy: Math.sin(a) * v,
        w: 6 + Math.random() * 6,
        h: 3 + Math.random() * 4,
        r: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 14,
        flip: Math.random() * Math.PI,
        vf: 6 + Math.random() * 8,
        color: this.colors[i % this.colors.length],
        life: 2.4 + Math.random() * 1.2,
        age: 0,
      });
    }
    if (!this.raf) {
      this.last = performance.now();
      this.raf = requestAnimationFrame((t) => this.frame(t));
    }
  }

  frame(now) {
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    const { g, dpr } = this;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, this.canvas.width, this.canvas.height);
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const drag = Math.exp(-1.8 * dt);
    this.parts = this.parts.filter((p) => {
      p.age += dt;
      p.vx *= drag;
      p.vy = p.vy * drag + 980 * dt;
      p.x += p.vx * dt + Math.sin(p.flip) * 20 * dt;
      p.y += p.vy * dt;
      p.r += p.vr * dt;
      p.flip += p.vf * dt;
      const fade = Math.min(1, (p.life - p.age) / 0.5);
      if (fade <= 0 || p.y > innerHeight + 40) return false;
      g.save();
      g.globalAlpha = fade;
      g.translate(p.x, p.y);
      g.rotate(p.r);
      g.scale(1, Math.cos(p.flip));
      g.fillStyle = p.color;
      g.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      g.restore();
      return true;
    });
    if (this.parts.length) this.raf = requestAnimationFrame((t) => this.frame(t));
    else {
      g.setTransform(1, 0, 0, 1, 0, 0);
      g.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.raf = 0;
    }
  }
}
