// Everything that moves on its own or answers the duel: tumbleweeds, dust devils, motes in the low light, lantern
// glows, a crow, and the shot itself: muzzle flash, the bullet and its stretched trail, smoke, sparks, dust puffs,
// and the hat's flight and bounce.
import * as THREE from "three";
import { softDot } from "./materials.js";
import { seeded } from "./kit.js";

const pointVertex = /* glsl */ `
  attribute float aSize;
  attribute float aAlpha;
  uniform float uScale;
  varying float vAlpha;
  #include <fog_pars_vertex>
  void main() {
    vAlpha = aAlpha;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize * uScale / max(0.1, -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
    #include <fog_vertex>
  }
`;
const pointFragment = /* glsl */ `
  uniform sampler2D uMap;
  uniform vec3 uColor;
  varying float vAlpha;
  #include <fog_pars_fragment>
  void main() {
    vec4 t = texture2D(uMap, gl_PointCoord);
    gl_FragColor = vec4(uColor, t.a * vAlpha);
    if (gl_FragColor.a < 0.003) discard;
    #include <fog_fragment>
  }
`;

/** A pool of soft points with per-point size and alpha; positions and those two are written each frame. */
class PointPool {
  constructor(count, { color, additive = false, map, fog = true, depthWrite = false }) {
    this.count = count;
    this.geometry = new THREE.BufferGeometry();
    this.position = new Float32Array(count * 3);
    this.size = new Float32Array(count);
    this.alpha = new Float32Array(count);
    this.geometry.setAttribute("position", new THREE.BufferAttribute(this.position, 3).setUsage(THREE.DynamicDrawUsage));
    this.geometry.setAttribute("aSize", new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    this.geometry.setAttribute("aAlpha", new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    this.material = new THREE.ShaderMaterial({
      uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { uScale: { value: 400 }, uMap: { value: null }, uColor: { value: new THREE.Color() } }]),
      vertexShader: pointVertex,
      fragmentShader: pointFragment,
      transparent: true,
      depthWrite,
      fog,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    this.material.uniforms.uMap.value = map;
    this.material.uniforms.uColor.value.copy(color);
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.frustumCulled = false;
  }
  flush() {
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.aSize.needsUpdate = true;
    this.geometry.attributes.aAlpha.needsUpdate = true;
  }
}

/** Short-lived particles: puffs, smoke, sparks. */
class Burst extends PointPool {
  constructor(count, opts) {
    super(count, opts);
    this.vel = new Float32Array(count * 3);
    this.life = new Float32Array(count);
    this.max = new Float32Array(count).fill(1);
    this.grow = new Float32Array(count);
    this.base = new Float32Array(count);
    this.peak = new Float32Array(count);
    this.next = 0;
    this.drag = opts.drag ?? 2.5;
    this.gravity = opts.gravity ?? 0;
  }
  emit(p, v, { life = 1, size = 0.3, grow = 1, alpha = 0.6 } = {}) {
    const i = this.next;
    this.next = (this.next + 1) % this.count;
    this.position.set([p.x, p.y, p.z], i * 3);
    this.vel.set([v.x, v.y, v.z], i * 3);
    this.life[i] = life;
    this.max[i] = life;
    this.base[i] = size;
    this.grow[i] = grow;
    this.peak[i] = alpha;
  }
  update(dt) {
    const drag = Math.exp(-this.drag * dt);
    for (let i = 0; i < this.count; i += 1) {
      if (this.life[i] <= 0) {
        this.alpha[i] = 0;
        continue;
      }
      this.life[i] -= dt;
      const k = i * 3;
      this.vel[k] *= drag;
      this.vel[k + 1] = this.vel[k + 1] * drag + this.gravity * dt;
      this.vel[k + 2] *= drag;
      this.position[k] += this.vel[k] * dt;
      this.position[k + 1] += this.vel[k + 1] * dt;
      this.position[k + 2] += this.vel[k + 2] * dt;
      const age = 1 - Math.max(0, this.life[i]) / this.max[i];
      this.size[i] = this.base[i] * (1 + this.grow[i] * age);
      this.alpha[i] = this.peak[i] * Math.min(1, age * 8) * (1 - age) * (1 - age);
    }
    this.flush();
  }
}

function tumbleweedGeometry(rnd) {
  const parts = [];
  for (let i = 0; i < 14; i += 1) {
    const g = new THREE.TorusGeometry(0.34 + rnd() * 0.08, 0.014, 3, 18, Math.PI * (1.2 + rnd() * 0.8));
    g.rotateX(rnd() * Math.PI);
    g.rotateY(rnd() * Math.PI);
    g.rotateZ(rnd() * Math.PI);
    parts.push(g.toNonIndexed());
  }
  for (let i = 0; i < 8; i += 1) {
    const g = new THREE.TorusGeometry(0.2 + rnd() * 0.08, 0.012, 3, 12, Math.PI * 1.5);
    g.rotateX(rnd() * Math.PI);
    g.rotateY(rnd() * Math.PI);
    parts.push(g.toNonIndexed());
  }
  let n = 0;
  for (const g of parts) n += g.attributes.position.count;
  const pos = new Float32Array(n * 3);
  const nor = new Float32Array(n * 3);
  let o = 0;
  for (const g of parts) {
    pos.set(g.attributes.position.array, o * 3);
    nor.set(g.attributes.normal.array, o * 3);
    o += g.attributes.position.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  return out;
}

function flashTexture() {
  const S = 128;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.18, "rgba(255,240,200,0.9)");
  grad.addColorStop(0.45, "rgba(255,170,80,0.25)");
  grad.addColorStop(1, "rgba(255,120,40,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, S, S);
  g.globalCompositeOperation = "lighter";
  g.translate(S / 2, S / 2);
  for (let i = 0; i < 7; i += 1) {
    g.rotate((Math.PI * 2) / 7 + (i % 2) * 0.2);
    const spike = g.createLinearGradient(0, 0, S / 2, 0);
    spike.addColorStop(0, "rgba(255,240,210,0.9)");
    spike.addColorStop(1, "rgba(255,160,60,0)");
    g.fillStyle = spike;
    g.beginPath();
    g.moveTo(0, -4);
    g.lineTo(S / 2, 0);
    g.lineTo(0, 4);
    g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  return t;
}

export function createEffects(scene, tokens, tier, lanterns) {
  const rnd = seeded(5150);
  const dot = softDot(64);
  const soft = softDot(64, 0.0);
  const group = new THREE.Group();
  scene.add(group);
  const scale = tier.particles;

  // dust puffs and smoke
  const dust = new Burst(Math.round(140 * Math.max(0.6, scale)), { color: tokens.dust.clone().lerp(tokens.ground, 0.4), map: soft, drag: 3.2, gravity: 0.15 });
  const smoke = new Burst(48, { color: new THREE.Color(0.82, 0.8, 0.78).lerp(tokens.skyHorizon, 0.3), map: soft, drag: 1.6, gravity: 0.35 });
  const sparks = new Burst(48, { color: new THREE.Color(1.0, 0.75, 0.4), map: dot, additive: true, drag: 1.2, gravity: -6 });
  group.add(dust.points, smoke.points, sparks.points);

  // motes drifting in the light
  const moteCount = Math.round(170 * scale);
  const motes = new PointPool(moteCount, { color: tokens.dust.clone().multiplyScalar(1.2), map: dot, additive: true, fog: false });
  const moteSeed = [];
  for (let i = 0; i < moteCount; i += 1) {
    moteSeed.push({ x: (rnd() - 0.5) * 16, y: 0.2 + rnd() * 4.5, z: -10 + rnd() * 18, p: rnd() * 100, s: 0.025 + rnd() * 0.05 });
  }
  group.add(motes.points);

  // dust devils down the street
  const devilCount = Math.round(260 * scale);
  const devil = new PointPool(devilCount, { color: tokens.dust.clone().lerp(tokens.ground, 0.55), map: soft });
  const devilSeed = [];
  for (let i = 0; i < devilCount; i += 1) devilSeed.push({ a: rnd() * Math.PI * 2, y: rnd(), w: 1.2 + rnd() * 2.2, j: rnd() });
  const devilState = { active: false, t: 0, dur: 13, z: -48, from: -30, to: 30, nextAt: 2.2 };
  group.add(devil.points);

  // lantern glows: brighter the more the theme lights them
  const glow = new PointPool(Math.max(1, lanterns.length), { color: tokens.lantern.clone().multiplyScalar(1.4), map: soft, additive: true });
  lanterns.forEach((p, i) => {
    glow.position.set([p.x, p.y, p.z], i * 3);
    glow.size[i] = 1.4;
    glow.alpha[i] = Math.max(0, tokens.lanternOn) * 0.9;
  });
  glow.flush();
  group.add(glow.points);

  // tumbleweeds
  const weedMat = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.62, 0.48, 0.3).lerp(tokens.ground, 0.25), roughness: 1, envMapIntensity: 0.4 });
  const weeds = [0, 1].map(() => {
    const mesh = new THREE.Mesh(tumbleweedGeometry(rnd), weedMat);
    mesh.castShadow = true;
    mesh.visible = false;
    group.add(mesh);
    return { mesh, active: false, x: 0, z: 0, dir: 1, speed: 3, phase: 0, hop: 0.5, nextAt: 0, r: 0.4 };
  });
  weeds[0].nextAt = 0.4;
  weeds[1].nextAt = 9;

  // the crow
  const crow = new THREE.Group();
  const crowMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.03, 0.03, 0.04), side: THREE.DoubleSide, fog: true });
  const body = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.7, 6).rotateZ(-Math.PI / 2), crowMat);
  const wingGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0.12, 0, 0), new THREE.Vector3(-0.2, 0, 0), new THREE.Vector3(-0.05, 0, 0.75), new THREE.Vector3(0.12, 0, 0), new THREE.Vector3(-0.05, 0, 0.75), new THREE.Vector3(0.18, 0, 0.55)]);
  wingGeo.computeVertexNormals();
  const wingL = new THREE.Mesh(wingGeo, crowMat);
  const wingR = new THREE.Mesh(wingGeo, crowMat);
  wingR.scale.z = -1;
  crow.add(body, wingL, wingR);
  crow.visible = false;
  crow.scale.setScalar(1.6);
  group.add(crow);
  const crowState = { active: false, t: 0, dur: 9, y: 17, z: -36, dir: 1 };

  // the bullet: a hot capsule, a stretched trail, and a glow
  const bullet = new THREE.Group();
  const slug = new THREE.Mesh(new THREE.CapsuleGeometry(0.042, 0.15, 4, 12).rotateZ(Math.PI / 2), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.25, 0.9, 0.48) }));
  const trailGeo = new THREE.CylinderGeometry(0.04, 0.0, 1, 12, 1, true).rotateZ(Math.PI / 2).translate(-0.5, 0, 0);
  const trailMat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(1.9, 0.95, 0.38) } },
    vertexShader: "varying float vX; void main(){ vX = position.x; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: "uniform vec3 uColor; varying float vX; void main(){ float a = pow(clamp(1.0 + vX, 0.0, 1.0), 2.2); gl_FragColor = vec4(uColor * a, a); }",
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  const trail = new THREE.Mesh(trailGeo, trailMat);
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: new THREE.Color(0.6, 0.36, 0.16), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  halo.scale.setScalar(0.12);
  bullet.add(trail, slug, halo);
  bullet.visible = false;
  group.add(bullet);
  const shot = { active: false, from: new THREE.Vector3(), to: new THREE.Vector3(), dir: new THREE.Vector3(), t: 0, dist: 1, speed: 26, onHit: null, done: false };

  // muzzle flash
  const flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: flashTexture(), color: new THREE.Color(3, 2.4, 1.6), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  flash.visible = false;
  group.add(flash);
  const flashState = { t: 1 };

  // the hat's flight
  const hatState = { hat: null, vel: new THREE.Vector3(), spin: new THREE.Vector3(), active: false, bounces: 0, onLand: null, rest: 0 };

  const tmp = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);

  function puff(p, n = 14, strength = 1) {
    for (let i = 0; i < n; i += 1) {
      const a = rnd() * Math.PI * 2;
      const s = (0.6 + rnd() * 1.6) * strength;
      dust.emit(tmp.set(p.x + Math.cos(a) * 0.1, Math.max(0.04, p.y), p.z + Math.sin(a) * 0.1), new THREE.Vector3(Math.cos(a) * s, 0.25 + rnd() * 0.9 * strength, Math.sin(a) * s), {
        life: 0.9 + rnd() * 1.1,
        size: 0.22 + rnd() * 0.3,
        grow: 2.4,
        alpha: 0.55,
      });
    }
  }

  return {
    group,
    dust,
    bullet,

    /** Starts a shot from `from` to `to`; onHit fires when it arrives. Times are in game seconds. */
    fire(from, to, onHit) {
      shot.from.copy(from);
      shot.to.copy(to);
      shot.dir.copy(to).sub(from).normalize();
      shot.dist = from.distanceTo(to);
      shot.t = 0;
      shot.active = true;
      shot.done = false;
      shot.onHit = onHit;
      bullet.visible = true;
      bullet.position.copy(from);
      bullet.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), shot.dir);
      trail.scale.set(0.01, 1, 1);
      flash.position.copy(from).addScaledVector(shot.dir, 0.12);
      flash.visible = true;
      flash.material.rotation = rnd() * Math.PI;
      flashState.t = 0;
      for (let i = 0; i < 10; i += 1) {
        smoke.emit(tmp.copy(from).addScaledVector(shot.dir, 0.1), new THREE.Vector3(shot.dir.x * (0.6 + rnd()), 0.1 + rnd() * 0.3, shot.dir.z * (0.6 + rnd()) + (rnd() - 0.5) * 0.4), { life: 1.6 + rnd(), size: 0.12, grow: 4.5, alpha: 0.42 });
      }
      for (let i = 0; i < 16; i += 1) {
        sparks.emit(tmp.copy(from), new THREE.Vector3(shot.dir.x * (3 + rnd() * 5) + (rnd() - 0.5) * 2, (rnd() - 0.2) * 2.5, shot.dir.z * (3 + rnd() * 5) + (rnd() - 0.5) * 2), { life: 0.25 + rnd() * 0.25, size: 0.05, grow: -0.5, alpha: 1 });
      }
    },

    /** A dry click: a few sparks and a puff of dust off the gun. */
    misfire(from) {
      for (let i = 0; i < 6; i += 1) {
        sparks.emit(tmp.copy(from), new THREE.Vector3((rnd() - 0.5) * 1.5, rnd() * 1.5, (rnd() - 0.5) * 1.5), { life: 0.2, size: 0.03, grow: 0, alpha: 0.8 });
      }
    },

    bulletPosition(target) {
      return target.copy(bullet.position);
    },

    shotActive: () => shot.active,

    /** Sends the hat flying from the head it sat on, away from the shooter. */
    launchHat(hat, scene, awayX) {
      scene.attach(hat);
      hatState.hat = hat;
      hatState.active = true;
      hatState.bounces = 0;
      hatState.vel.set(awayX * (1.2 + rnd() * 0.4), 4.3 + rnd() * 0.4, 0.9 + rnd() * 0.4);
      hatState.spin.set(-6 - rnd() * 4, rnd() * 3, awayX * -9);
    },

    hatFlying: () => hatState.active,

    /** Stops a shot or a hat in flight, for a round that ends early. */
    reset() {
      hatState.active = false;
      hatState.hat = null;
      shot.active = false;
      shot.onHit = null;
      bullet.visible = false;
      flash.visible = false;
    },

    puff,

    startCrow(dir = 1) {
      crowState.active = true;
      crowState.t = 0;
      crowState.dir = dir;
      crow.visible = true;
    },

    retint(t) {
      glow.material.uniforms.uColor.value.copy(t.lantern).multiplyScalar(1.4);
      for (let i = 0; i < glow.count; i += 1) glow.alpha[i] = Math.max(0, t.lanternOn) * 0.9;
      glow.flush();
    },

    setScale(pixels) {
      for (const pool of [dust, smoke, sparks, motes, devil, glow]) pool.material.uniforms.uScale.value = pixels;
    },

    /** dt: game seconds; real: wall seconds (motes and the ambient world keep real time). */
    update(dt, real, time, camera, events) {
      // shot
      if (shot.active) {
        shot.t += dt;
        const d = Math.min(shot.dist, shot.t * shot.speed);
        bullet.position.copy(shot.from).addScaledVector(shot.dir, d);
        const trailLen = Math.min(d, 2.2);
        trail.scale.set(Math.max(0.01, trailLen), 1, 1);
        halo.material.opacity = 0.9 + Math.sin(time * 60) * 0.1;
        if (d >= shot.dist) {
          shot.active = false;
          bullet.visible = false;
          for (let i = 0; i < 18; i += 1) sparks.emit(tmp.copy(shot.to), new THREE.Vector3(shot.dir.x * 2 + (rnd() - 0.5) * 4, rnd() * 3, (rnd() - 0.5) * 4), { life: 0.3 + rnd() * 0.3, size: 0.045, grow: 0, alpha: 1 });
          if (shot.onHit) shot.onHit();
        }
      }
      if (flash.visible) {
        flashState.t += dt;
        const f = flashState.t;
        const s = f < 0.03 ? f / 0.03 : Math.max(0, 1 - (f - 0.03) / 0.09);
        flash.scale.setScalar(0.9 * s + 0.05);
        flash.material.opacity = s;
        if (f > 0.13) flash.visible = false;
      }

      // hat
      if (hatState.active && hatState.hat) {
        const h = hatState.hat;
        hatState.vel.y -= 9.8 * dt;
        h.position.addScaledVector(hatState.vel, dt);
        h.rotation.x += hatState.spin.x * dt;
        h.rotation.y += hatState.spin.y * dt;
        h.rotation.z += hatState.spin.z * dt;
        if (h.position.y < 0.05 && hatState.vel.y < 0) {
          h.position.y = 0.05;
          hatState.bounces += 1;
          puff(h.position, 10, 0.6 + 0.4 / hatState.bounces);
          events?.("hat-land", hatState.bounces);
          if (hatState.bounces >= 3 || Math.abs(hatState.vel.y) < 0.9) {
            hatState.active = false;
            hatState.vel.set(0, 0, 0);
            // settle brim-down, as a hat lands
            h.rotation.set(0, h.rotation.y, 0);
          } else {
            hatState.vel.y *= -0.38;
            hatState.vel.x *= 0.55;
            hatState.vel.z *= 0.55;
            hatState.spin.multiplyScalar(0.45);
          }
        }
      }

      // tumbleweeds
      for (const w of weeds) {
        if (!w.active) {
          if (time > w.nextAt) {
            w.active = true;
            w.dir = rnd() < 0.5 ? 1 : -1;
            w.x = -w.dir * 15;
            w.z = -7 + rnd() * 9;
            w.speed = 2.6 + rnd() * 1.8;
            w.phase = 0;
            w.r = 0.36 + rnd() * 0.12;
            w.mesh.scale.setScalar(w.r / 0.4);
            w.mesh.visible = true;
          }
          continue;
        }
        w.x += w.dir * w.speed * real;
        w.phase += real * w.speed * 0.55;
        const hop = Math.abs(Math.sin(w.phase * Math.PI)) * (0.35 + 0.25 * Math.sin(w.phase * 0.7));
        const prevY = w.mesh.position.y;
        w.mesh.position.set(w.x, w.r + hop, w.z + Math.sin(w.phase * 0.8) * 0.4);
        w.mesh.rotation.z -= (w.dir * w.speed * real) / w.r;
        w.mesh.rotation.x += real * 0.6;
        if (prevY > w.r + 0.03 && w.mesh.position.y <= w.r + 0.03) puff(tmp.set(w.x, 0.05, w.mesh.position.z), 4, 0.35);
        if (Math.abs(w.x) > 16) {
          w.active = false;
          w.mesh.visible = false;
          w.nextAt = time + 7 + rnd() * 9;
        }
      }

      // dust devil
      if (!devilState.active && time > devilState.nextAt) {
        devilState.active = true;
        devilState.t = 0;
        const dir = rnd() < 0.5 ? 1 : -1;
        devilState.from = -dir * 34;
        devilState.to = dir * 34;
        devilState.z = -40 - rnd() * 30;
      }
      if (devilState.active) {
        devilState.t += real;
        const p = devilState.t / devilState.dur;
        const env = Math.sin(Math.min(1, p) * Math.PI);
        const cx = devilState.from + (devilState.to - devilState.from) * p;
        const cz = devilState.z + Math.sin(p * 5) * 3;
        const H = 9;
        for (let i = 0; i < devil.count; i += 1) {
          const s = devilSeed[i];
          s.y = (s.y + real * (0.07 + s.j * 0.05)) % 1;
          const rad = (0.35 + s.y * s.y * s.w * 2.2) * (0.8 + 0.2 * Math.sin(time * 3 + s.j * 10));
          s.a += real * (4.5 / (0.6 + rad));
          const k = i * 3;
          const lean = s.y * s.y * 2.2;
          devil.position[k] = cx + Math.cos(s.a) * rad + lean;
          devil.position[k + 1] = s.y * H;
          devil.position[k + 2] = cz + Math.sin(s.a) * rad;
          devil.size[i] = 0.7 + s.y * 2.0;
          devil.alpha[i] = env * 0.3 * (1 - s.y) * Math.min(1, s.y * 8);
        }
        devil.flush();
        if (p >= 1) {
          devilState.active = false;
          devilState.nextAt = time + 9 + rnd() * 10;
          devil.alpha.fill(0);
          devil.flush();
        }
      }

      // motes
      for (let i = 0; i < motes.count; i += 1) {
        const m = moteSeed[i];
        const k = i * 3;
        motes.position[k] = m.x + Math.sin(time * 0.21 + m.p) * 0.6;
        motes.position[k + 1] = m.y + Math.sin(time * 0.37 + m.p * 2) * 0.25;
        motes.position[k + 2] = m.z + Math.cos(time * 0.17 + m.p) * 0.5;
        motes.size[i] = m.s;
        motes.alpha[i] = 0.25 + 0.25 * Math.sin(time * 0.9 + m.p * 3);
      }
      motes.flush();

      // crow
      if (crowState.active) {
        crowState.t += real;
        const p = crowState.t / crowState.dur;
        const x = (-60 + p * 120) * crowState.dir;
        crow.position.set(x, crowState.y + Math.sin(p * 9) * 0.8, crowState.z);
        crow.rotation.y = crowState.dir > 0 ? 0 : Math.PI;
        const flap = Math.sin(crowState.t * 11) * 0.7;
        wingL.rotation.x = -flap;
        wingR.rotation.x = flap;
        if (p >= 1) {
          crowState.active = false;
          crow.visible = false;
        }
      }

      dust.update(dt);
      smoke.update(dt);
      sparks.update(dt);
    },
  };
}
