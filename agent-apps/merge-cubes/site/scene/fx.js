// The bloom pass, with its threshold set so only a merge's flash (and the white-hot top of the ramp) flares, the burst
// of light a merge gives off round the cube's foot, the six sparks that fly off its struck side, the pool of light a
// lit cube spills on the tray, and the motes that drift through the light on an evening stage.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { sparkMaterial } from "./materials.js";

export function createPost(renderer, scene, camera, tier) {
  if (!tier.bloom) {
    // No bloom pass on this tier: the scene draws straight to the canvas with the context's own antialiasing.
    return { on: false, setOn() {}, apply() {}, setBoost() {}, setSize() {}, render: () => renderer.render(scene, camera) };
  }
  const size = renderer.getSize(new THREE.Vector2());
  const target = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x * tier.bloomScale, size.y * tier.bloomScale), 0.8, 0.5, 0.9);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  let on = true;
  let boost = 0;
  let base = { strength: 0.8, radius: 0.5, threshold: 0.9 };
  return {
    get on() {
      return on;
    },
    setOn(value) {
      on = value;
    },
    apply(tokens) {
      base = { strength: tokens.bloomStrength, radius: tokens.bloomRadius, threshold: tokens.bloomThreshold };
      bloom.radius = base.radius;
      bloom.threshold = base.threshold;
    },
    /** A brief lift in bloom strength for the 2048 moment. */
    setBoost(value) {
      boost = value;
    },
    setSize(w, h, ratio) {
      composer.setPixelRatio(ratio);
      composer.setSize(w, h);
      bloom.resolution.set(w * ratio * tier.bloomScale, h * ratio * tier.bloomScale);
    },
    render(dt) {
      bloom.strength = base.strength * (1 + boost * 0.35);
      if (on) composer.render(dt);
      else renderer.render(scene, camera);
    },
  };
}

const SPARKS = 72;
const GRAVITY = -9;
const SPARK_LIFE = 0.5;

export function createSparks(scene) {
  // A spark is a slim diamond, longer than it is wide, so six of them read as six bright points, never a haze.
  const geo = new THREE.OctahedronGeometry(0.05, 0).scale(1, 1.9, 1);
  const mesh = new THREE.InstancedMesh(geo, sparkMaterial(), SPARKS);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.renderOrder = 4;
  const color = new THREE.Color();
  const live = [];
  for (let i = 0; i < SPARKS; i += 1) {
    live.push({ life: 0, p: new THREE.Vector3(), v: new THREE.Vector3(), spin: new THREE.Vector3(), r: new THREE.Euler() });
    mesh.setColorAt(i, color.setRGB(0, 0, 0));
  }
  scene.add(mesh);
  let cursor = 0;
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const s = new THREE.Vector3();
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  for (let i = 0; i < SPARKS; i += 1) mesh.setMatrixAt(i, zero);
  // Six headings fanned along the struck face, three to each side: near the face, then wider, then wide and back.
  const FAN = [0.35, 0.8, 1.25];

  return {
    /** Six sparks off the struck face (the side the pair met on), fanned out low across the tray, three each way. */
    puff(x, z, dir, tint, power, top = 0.7) {
      const dx = dir === "left" ? -1 : dir === "right" ? 1 : 0;
      const dz = dir === "up" ? -1 : dir === "down" ? 1 : 0;
      const sideX = -dz;
      const sideZ = dx;
      for (let k = 0; k < 6; k += 1) {
        const sp = live[cursor];
        mesh.setColorAt(cursor, color.copy(tint).multiplyScalar(power));
        cursor = (cursor + 1) % SPARKS;
        const sign = k % 2 === 0 ? 1 : -1;
        const a = FAN[k >> 1];
        const out = Math.sin(a) * sign;
        const back = Math.cos(a);
        const speed = 2.3 + (k >> 1) * 0.35;
        sp.p.set(x - dx * 0.5 + sideX * out * 0.3, top * 0.45, z - dz * 0.5 + sideZ * out * 0.3);
        sp.v.set((sideX * out - dx * back) * speed, 1.5 + (k >> 1) * 0.3, (sideZ * out - dz * back) * speed);
        sp.spin.set(6 + k, 9 - k, 4 + k * 0.5);
        sp.r.set(0, 0, 0);
        sp.life = 1;
      }
      mesh.instanceColor.needsUpdate = true;
    },
    update(dt) {
      let any = false;
      for (let i = 0; i < SPARKS; i += 1) {
        const sp = live[i];
        if (sp.life <= 0) continue;
        any = true;
        sp.life -= dt / SPARK_LIFE;
        if (sp.life <= 0) {
          mesh.setMatrixAt(i, zero);
          continue;
        }
        sp.v.y += GRAVITY * dt;
        sp.p.addScaledVector(sp.v, dt);
        if (sp.p.y < 0.04) {
          sp.p.y = 0.04;
          sp.v.y *= -0.35;
          sp.v.x *= 0.6;
          sp.v.z *= 0.6;
        }
        sp.r.x += sp.spin.x * dt;
        sp.r.y += sp.spin.y * dt;
        sp.r.z += sp.spin.z * dt;
        const k = Math.max(0.0001, sp.life ** 0.6);
        m.compose(sp.p, q.setFromEuler(sp.r), s.set(k, k, k));
        mesh.setMatrixAt(i, m);
      }
      if (any) mesh.instanceMatrix.needsUpdate = true;
    },
  };
}

let sharedGlow = null;
/** A soft round glow, white, for every sprite that lights the stage. */
export function glowTexture() {
  if (sharedGlow) return sharedGlow;
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(255, 255, 255, 1)");
  g.addColorStop(0.18, "rgba(255, 255, 255, 0.8)");
  g.addColorStop(0.45, "rgba(255, 255, 255, 0.22)");
  g.addColorStop(1, "rgba(255, 255, 255, 0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  sharedGlow = new THREE.CanvasTexture(canvas);
  return sharedGlow;
}

let sharedPool = null;
/** A soft rounded square of light, brightest at a cube's foot and gone half a cell out, for the pool on the tray. */
export function poolTexture() {
  if (sharedPool) return sharedPool;
  const px = 128;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.filter = `blur(${px * 0.075}px)`;
  ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
  ctx.beginPath();
  ctx.roundRect(px * 0.27, px * 0.27, px * 0.46, px * 0.46, px * 0.09);
  ctx.fill();
  ctx.filter = `blur(${px * 0.035}px)`;
  ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
  ctx.beginPath();
  ctx.roundRect(px * 0.3, px * 0.3, px * 0.4, px * 0.4, px * 0.07);
  ctx.fill();
  sharedPool = new THREE.CanvasTexture(canvas);
  sharedPool.colorSpace = THREE.SRGBColorSpace;
  return sharedPool;
}

/**
 * The burst of light a merge gives off: a hot white core and a halo in the cube's color that swell and fade in half a
 * second. It is bright enough for the bloom pass to flare round it, and still reads as a flash when bloom is off.
 */
export function createFlares(scene) {
  const map = glowTexture();
  const pool = [];
  for (let i = 0; i < 6; i += 1) {
    // Both are drawn under the cubes (before any cube body), so the burst lights the tray round the cube and never
    // lies over a cube or its number.
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
    const core = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
    halo.renderOrder = 1;
    core.renderOrder = 1;
    halo.visible = false;
    core.visible = false;
    scene.add(halo, core);
    pool.push({ halo, core, t: 1, size: 1, power: 1, color: new THREE.Color() });
  }
  let next = 0;
  const white = new THREE.Color(1, 1, 1);
  // The glow the winning cube hangs in: drawn under every cube, so it lights the tray and the air round it without
  // washing out any face.
  const aura = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
  aura.visible = false;
  aura.renderOrder = 1;
  scene.add(aura);
  const auraColor = new THREE.Color();
  let auraLevel = 0;
  let auraTo = 0;
  let auraTime = 0;
  return {
    /** Holds the glow round a point (the winning cube) until released. */
    hold(position, tint) {
      aura.position.copy(position);
      auraColor.copy(tint).lerp(white, 0.35);
      auraTo = 1;
    },
    release() {
      auraTo = 0;
    },
    /** Shows (or hides again) every sprite, so the first frame that draws them never waits on a compile. */
    warm(on) {
      for (const f of pool) {
        f.halo.visible = on;
        f.core.visible = on;
        f.t = on ? 0 : 1;
      }
      aura.visible = on;
      auraLevel = 0;
    },
    /** A burst at a point; `power` (0 to 1) climbs with the cube's value, so a 4 gives a glint and a 1024 a flare. */
    flare(x, y, z, tint, size, power = 1) {
      const f = pool[next];
      next = (next + 1) % pool.length;
      f.t = 0;
      f.size = size;
      f.power = power;
      f.color.copy(tint).lerp(white, 0.25);
      f.halo.position.set(x, y, z);
      f.core.position.set(x, y + 0.05, z);
      f.halo.visible = true;
      f.core.visible = true;
    },
    update(dt) {
      auraTime += dt;
      auraLevel += (auraTo - auraLevel) * Math.min(1, dt * 4);
      aura.visible = auraLevel > 0.01;
      if (aura.visible) {
        aura.scale.setScalar(3.2 + 0.2 * Math.sin(auraTime * 2.4));
        aura.material.color.copy(auraColor).multiplyScalar(1.1 * auraLevel);
      }
      for (const f of pool) {
        if (!f.halo.visible) continue;
        f.t += dt / 0.34;
        if (f.t >= 1) {
          f.halo.visible = false;
          f.core.visible = false;
          continue;
        }
        const grow = 1 - (1 - Math.min(1, f.t * 2.2)) ** 3;
        const fade = (1 - f.t) ** 1.6;
        f.halo.scale.setScalar(f.size * (1.15 + 0.9 * grow));
        f.halo.material.color.copy(f.color).multiplyScalar(2.6 * fade * f.power);
        const spark = Math.max(0, 1 - f.t * 2.4);
        f.core.scale.setScalar(f.size * (1 + 0.5 * grow));
        f.core.material.color.copy(f.color).lerp(white, 0.5).multiplyScalar(1.6 * spark * spark * f.power);
      }
    },
  };
}

function moteTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255, 255, 255, 1)");
  g.addColorStop(0.35, "rgba(255, 255, 255, 0.35)");
  g.addColorStop(1, "rgba(255, 255, 255, 0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

/** Soft motes drifting up through the light, out of focus, on the evening stages. */
export function createMotes(scene) {
  const count = 46;
  const pos = new Float32Array(count * 3);
  const seeds = [];
  for (let i = 0; i < count; i += 1) {
    const a = (i / count) * Math.PI * 2 * 7.3;
    const r = 3.2 + ((i * 37) % 23) / 3.5;
    seeds.push({ a, r, y: ((i * 53) % 41) / 41, speed: 0.04 + ((i * 17) % 11) / 260 });
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({ size: 0.22, map: moteTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  points.renderOrder = 4;
  scene.add(points);
  let t = 0;
  return {
    apply(tokens) {
      points.visible = tokens.bokehPower > 0;
      mat.color.copy(tokens.bokeh).multiplyScalar(0.55 * tokens.bokehPower);
    },
    update(dt, reduced) {
      if (!points.visible) return;
      if (!reduced) t += dt;
      for (let i = 0; i < count; i += 1) {
        const s = seeds[i];
        const y = (s.y + t * s.speed) % 1;
        const a = s.a + t * 0.03 + Math.sin(t * 0.4 + i) * 0.05;
        pos[i * 3] = Math.cos(a) * s.r;
        pos[i * 3 + 1] = -1.5 + y * 5.5;
        pos[i * 3 + 2] = Math.sin(a) * s.r;
      }
      geo.attributes.position.needsUpdate = true;
      mat.opacity = 1;
    },
  };
}
