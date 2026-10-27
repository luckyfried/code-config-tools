// One round, staged: the wait (a slow dolly, the clock, a crow), DRAW (a flash, the word, a buzz), and either the
// shot (time drops to a tenth, the camera orbits the bullet, the hat flies) or a false start (a click, a jammed
// gun, a punch of the camera). Reaction times come from event.timeStamp against the moment DRAW was shown.
import * as THREE from "three";
import { easeInOut, easeOut } from "../scene/camera.js";

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const ORBIT_MS = 600;

export class Round {
  constructor({ world, hud, sound, loop, reduced, series, plan, ai = [null, null], onDone }) {
    this.world = world;
    this.hud = hud;
    this.sound = sound;
    this.loop = loop;
    this.reduced = reduced;
    this.series = series;
    this.plan = plan;
    this.ai = ai;
    this.onDone = onDone;
    this.phase = "idle";
    this.tasks = [];
    this.gameTasks = [];
    this.times = [null, null];
    this.winner = null;
    this.early = null;
    this.drawStamp = 0;
    this.finished = false;
  }

  at(ms, fn) {
    this.tasks.push({ at: performance.now() + ms, fn });
  }

  atGame(seconds, fn) {
    this.gameTasks.push({ at: this.loop.gameTime + seconds, fn });
  }

  start() {
    const { world, hud, sound, plan, reduced } = this;
    const [left, right] = world.figures;
    for (const f of world.figures) {
      f.restoreHat();
      f.reset();
      f.ready(true);
    }
    this.phase = "wait";
    this.waitStart = performance.now();
    this.drawAt = this.waitStart + plan.waitMs;
    hud.phase("waiting");
    hud.say(`Round ${plan.round}. Steady.`);
    const rig = world.rig;
    if (reduced) {
      rig.to(rig.frame.wide, 0.6);
    } else {
      const start = this.waitStart;
      const total = plan.waitMs + 400;
      rig.to(() => {
        const f = rig.frame;
        const e = easeInOut(clamp01((performance.now() - start) / total));
        return {
          pos: f.wide.pos.clone().lerp(f.close.pos, e),
          target: f.wide.target.clone().lerp(f.close.target, e),
          fov: f.wide.fov + (f.close.fov - f.wide.fov) * e,
          shift: f.wide.shift + (f.close.shift - f.wide.shift) * e,
        };
      }, 0.9);
      world.setDepthOfField(true);
    }
    // the clock, once a second
    for (let s = 1; s * 1000 < plan.waitMs; s += 1) this.at(s * 1000, () => this.phase === "wait" && sound.play(s % 2 ? "tick" : "tock", { gain: 0.55 }));
    // a crow crosses on the longer waits
    if (plan.waitMs > 3200) {
      const when = 900 + ((plan.round * 977) % 1000) / 1000 * (plan.waitMs - 2200);
      this.at(when, () => {
        if (this.phase !== "wait") return;
        world.effects.startCrow(plan.round % 2 ? 1 : -1);
        sound.play("crow", { gain: 0.5, pan: plan.round % 2 ? -0.4 : 0.4 });
      });
    }
    void left;
    void right;
  }

  /** A tap or key from `side` at `stamp` (performance time, ms). */
  press(side, stamp) {
    if (this.finished) return;
    if (this.phase === "wait") {
      if (stamp < this.waitStart + 150) return;
      this.falseStart(side);
      return;
    }
    if (this.phase === "draw") {
      const ms = Math.max(0, Math.round(stamp - this.drawStamp));
      this.times[side] = ms;
      this.hud.pressed(side);
      this.shoot(side);
      return;
    }
    if (this.phase === "shot" && this.times[side] === null && side !== this.winner) {
      this.times[side] = Math.max(0, Math.round(stamp - this.drawStamp));
      this.hud.pressed(side);
      this.world.figures[side].draw(this.loop.gameTime);
    }
  }

  showDraw() {
    const { hud, sound, world, reduced } = this;
    this.phase = "draw";
    this.drawStamp = performance.now();
    hud.phase("drawing");
    // under reduced motion the word fades in with no white frame
    if (!reduced) hud.flash();
    hud.say("Draw!");
    sound.play("draw", { gain: 0.8 });
    if (navigator.vibrate && navigator.userActivation?.hasBeenActive) {
      try {
        navigator.vibrate(70);
      } catch {
        // some browsers refuse vibration outside a gesture
      }
    }
    if (!reduced) world.rig.punch(0.12, 1.2);
    this.ai.forEach((ms, side) => {
      if (ms === null) return;
      const at = this.drawStamp + ms;
      this.tasks.push({ at, fn: () => this.press(side, at) });
    });
  }

  shoot(w) {
    const { world, hud, sound, loop, reduced } = this;
    this.phase = "shot";
    this.winner = w;
    hud.phase("shot");
    const shooter = world.figures[w];
    const target = world.figures[1 - w];
    shooter.draw(loop.gameTime);
    world.setDepthOfField(false);
    this.atGame(0.15, () => this.fire(shooter, target));
  }

  fire(shooter, target) {
    const { world, hud, sound, loop, reduced } = this;
    const now = loop.gameTime;
    shooter.fire(now);
    const from = shooter.muzzleWorld(new THREE.Vector3());
    const to = target.hatWorld(new THREE.Vector3());
    to.y += 0.06;
    const dir = Math.sign(to.x - from.x) || 1;
    world.lights.flash.position.copy(from);
    world.lights.flash.intensity = 60;
    this.flashUntil = performance.now() + 120;
    sound.play("gunshot", { gain: 1, pan: dir > 0 ? -0.35 : 0.35 });
    hud.flash(true);
    world.rig.punch(reduced ? 0.25 : 0.4, reduced ? 0 : 3);
    world.effects.fire(from, to, () => this.hit(shooter, target, dir));

    if (reduced) return;
    loop.timeScale(0.1);
    sound.play("slowmo", { gain: 0.7 });
    sound.wind(0.08, 0.15);
    const rig = world.rig;
    const t0 = performance.now();
    const portrait = rig.frame.portrait;
    const R = portrait ? 1.3 : 1.12;
    const center = new THREE.Vector3();
    const frozen = new THREE.Vector3();
    let held = false;
    const headAt = target.hatWorld(new THREE.Vector3());
    rig.to(() => {
      const p = clamp01((performance.now() - t0) / ORBIT_MS);
      const e = easeInOut(p);
      if (!held) {
        world.effects.bulletPosition(center);
        if (p >= 1) {
          frozen.copy(center);
          held = true;
        }
      }
      const c = held ? frozen : center;
      // a quarter turn of the view around the bullet: from its side to looking square down its path at the loser,
      // finishing a little off its shoulder so the capsule and its trail keep their length on screen
      const th = Math.pow(e, 1.3) * Math.PI * 0.42;
      const pos = new THREE.Vector3(c.x - dir * Math.sin(th) * R, c.y + 0.1 + Math.sin(th) * 0.08, c.z + Math.cos(th) * R);
      const look = c.clone().lerp(headAt, 0.12 + 0.88 * e);
      look.x += dir * 0.35 * (1 - e);
      look.z += 0.45 * e;
      return { pos, target: look, fov: portrait ? 50 : 36, shift: 0 };
    }, 0);
    this.at(ORBIT_MS, () => {
      loop.timeScale(1, 1.3);
      sound.wind(0.32, 0.8);
    });
  }

  hit(shooter, target, dir) {
    const { world, sound, loop, reduced } = this;
    const now = loop.gameTime;
    target.hit(now);
    target.hatOff = true;
    world.effects.launchHat(target.hat, world.scene, dir);
    sound.play("hit", { gain: 0.8 });
    world.effects.puff(target.hatWorld(new THREE.Vector3()), 8, 0.4);
    shooter.twirl(now + 0.55);
    if (!reduced) {
      const rig = world.rig;
      const portrait = rig.frame.portrait;
      const base = target.root.position.clone();
      const t0 = performance.now();
      rig.to(() => {
        const k = clamp01((performance.now() - t0) / 2400);
        const pos = new THREE.Vector3(base.x - dir * (portrait ? 1.2 : 2.4), 1.35 - k * 0.1, base.z + (portrait ? 6.0 : 5.4) - k * 0.5);
        const look = new THREE.Vector3(base.x + dir * (portrait ? 0.45 : 0.9), 1.45, base.z);
        return { pos, target: look, fov: portrait ? 56 : 44, shift: 0 };
      }, 0.75, easeOut);
    }
    this.at(reduced ? 900 : 1750, () => this.finish());
  }

  falseStart(side) {
    const { world, hud, sound, loop, reduced } = this;
    this.phase = "early";
    this.early = side;
    this.winner = 1 - side;
    const fig = world.figures[side];
    fig.jam(loop.gameTime);
    hud.pressed(side);
    hud.early(this.series.names[side]);
    hud.say(`${this.series.names[side]} jumped the gun.`);
    world.setDepthOfField(false);
    sound.play("click", { gain: 0.9 });
    sound.play("jam", { gain: 0.7, delay: 0.16 });
    this.at(160, () => world.effects.misfire(fig.muzzleWorld(new THREE.Vector3())));
    world.rig.punch(reduced ? 0 : 0.65, reduced ? 0 : 5);
    if (!reduced) {
      const rig = world.rig;
      const f = rig.frame;
      const base = fig.root.position.clone();
      rig.to(() => {
        const pos = f.wide.pos.clone().lerp(new THREE.Vector3(base.x * 0.55, 1.35, base.z + f.dist * 0.55), 0.6);
        const look = new THREE.Vector3(base.x * 0.7, 1.15, base.z - 4);
        return { pos, target: look, fov: f.wide.fov - 4, shift: f.wide.shift * 0.5 };
      }, 0.22, easeOut);
    }
    this.at(1500, () => this.finish());
  }

  finish() {
    if (this.finished) return;
    this.finished = true;
    this.phase = "done";
    this.hud.phase(null);
    this.onDone({ winner: this.winner, times: this.times.slice(), early: this.early });
  }

  /** Fixed-step update. */
  step() {
    const now = performance.now();
    if (this.phase === "wait" && now >= this.drawAt) this.showDraw();
    if (this.tasks.length) {
      const due = this.tasks.filter((t) => t.at <= now);
      if (due.length) {
        this.tasks = this.tasks.filter((t) => t.at > now);
        due.forEach((t) => t.fn());
      }
    }
    if (this.gameTasks.length) {
      const g = this.loop.gameTime;
      const due = this.gameTasks.filter((t) => t.at <= g);
      if (due.length) {
        this.gameTasks = this.gameTasks.filter((t) => t.at > g);
        due.forEach((t) => t.fn());
      }
    }
    if (this.flashUntil && now > this.flashUntil) {
      this.world.lights.flash.intensity *= 0.6;
      if (this.world.lights.flash.intensity < 0.1) {
        this.world.lights.flash.intensity = 0;
        this.flashUntil = 0;
      }
    }
  }
}
