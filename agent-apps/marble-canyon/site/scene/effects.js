// Contact juice: dust puffs at landings, a spark shower on a boost pad, confetti at the finish, and speed lines
// at the screen edges when the marble is flying.
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  DynamicDrawUsage,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  NormalBlending,
  Object3D,
  PlaneGeometry,
  Points,
  Quaternion,
  ShaderMaterial,
  Vector3,
} from "three";
import { createRng } from "../game/rng.js";

const rng = createRng(90210);

class ParticlePool {
  constructor(count, { additive, color, sizeScale }) {
    this.count = count;
    this.pos = new Float32Array(count * 3);
    this.vel = new Float32Array(count * 3);
    this.age = new Float32Array(count).fill(1);
    this.life = new Float32Array(count).fill(1);
    this.size = new Float32Array(count);
    this.grow = new Float32Array(count);
    this.alpha = new Float32Array(count);
    this.gravity = 0;
    this.drag = 0;
    this.next = 0;
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(this.pos, 3).setUsage(DynamicDrawUsage));
    geometry.setAttribute("aSize", new BufferAttribute(this.size, 1).setUsage(DynamicDrawUsage));
    geometry.setAttribute("aAlpha", new BufferAttribute(this.alpha, 1).setUsage(DynamicDrawUsage));
    this.material = new ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: additive ? AdditiveBlending : NormalBlending,
      uniforms: { color: { value: color.clone() }, scale: { value: sizeScale } },
      vertexShader: /* glsl */ `
        attribute float aSize;
        attribute float aAlpha;
        uniform float scale;
        varying float vAlpha;
        void main() {
          vAlpha = aAlpha;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * scale / max(0.1, -mv.z);
          gl_Position = projectionMatrix * mv;
        }
      `,
      fragmentShader: /* glsl */ `
        uniform vec3 color;
        varying float vAlpha;
        void main() {
          vec2 c = gl_PointCoord - 0.5;
          float d = length(c) * 2.0;
          float a = smoothstep(1.0, 0.2, d) * vAlpha;
          if (a < 0.01) discard;
          gl_FragColor = vec4(color, a);
          #include <colorspace_fragment>
        }
      `,
    });
    this.points = new Points(geometry, this.material);
    this.points.frustumCulled = false;
    this.geometry = geometry;
  }

  emit(p, v, life, size, grow) {
    const i = this.next;
    this.next = (this.next + 1) % this.count;
    for (let k = 0; k < 3; k += 1) {
      this.pos[i * 3 + k] = p[k];
      this.vel[i * 3 + k] = v[k];
    }
    this.age[i] = 0;
    this.life[i] = life;
    this.size[i] = size;
    this.grow[i] = grow;
  }

  update(dt) {
    let live = false;
    for (let i = 0; i < this.count; i += 1) {
      if (this.age[i] >= this.life[i]) {
        this.alpha[i] = 0;
        continue;
      }
      live = true;
      this.age[i] += dt;
      const k = this.age[i] / this.life[i];
      const o = i * 3;
      this.vel[o + 1] -= this.gravity * dt;
      const d = Math.exp(-this.drag * dt);
      this.vel[o] *= d;
      this.vel[o + 1] *= d;
      this.vel[o + 2] *= d;
      this.pos[o] += this.vel[o] * dt;
      this.pos[o + 1] += this.vel[o + 1] * dt;
      this.pos[o + 2] += this.vel[o + 2] * dt;
      this.size[i] += this.grow[i] * dt;
      this.alpha[i] = k < 0.12 ? k / 0.12 : Math.max(0, 1 - (k - 0.12) / 0.88);
    }
    if (live || this.wasLive) {
      this.geometry.attributes.position.needsUpdate = true;
      this.geometry.attributes.aSize.needsUpdate = true;
      this.geometry.attributes.aAlpha.needsUpdate = true;
    }
    this.wasLive = live;
  }
}

export function createEffects(tier, tokens, pixelRatio) {
  const scale = 300 * pixelRatio;
  const dust = new ParticlePool(Math.round(96 * tier.particles) + 16, {
    additive: false,
    color: tokens.floor.clone().lerp(new Color(0xffffff), 0.35),
    sizeScale: scale,
  });
  dust.gravity = -1.2;
  dust.drag = 2.6;
  const sparks = new ParticlePool(Math.round(140 * tier.particles) + 20, {
    additive: true,
    color: tokens.boost.clone().lerp(new Color(0xffffff), 0.35),
    sizeScale: scale,
  });
  sparks.gravity = 22;
  sparks.drag = 1.2;

  // Confetti: instanced paper bits with gravity, flutter drag, and spin.
  const confettiCount = Math.round(240 * tier.particles);
  const confettiGeometry = new PlaneGeometry(0.34, 0.2);
  const confetti = new InstancedMesh(confettiGeometry, new MeshBasicMaterial({ side: DoubleSide, toneMapped: false }), confettiCount);
  confetti.frustumCulled = false;
  confetti.instanceMatrix.setUsage(DynamicDrawUsage);
  const cPos = new Float32Array(confettiCount * 3);
  const cVel = new Float32Array(confettiCount * 3);
  const cAxis = [];
  const cAngle = new Float32Array(confettiCount);
  const cSpin = new Float32Array(confettiCount);
  const cAge = new Float32Array(confettiCount).fill(99);
  const zero = new Matrix4().makeScale(0, 0, 0);
  for (let i = 0; i < confettiCount; i += 1) {
    cAxis.push(new Vector3(rng() - 0.5, rng() - 0.5, rng() - 0.5).normalize());
    confetti.setMatrixAt(i, zero);
    confetti.setColorAt(i, new Color(0xffffff));
  }
  let confettiLive = false;
  const confettiColors = () => [tokens.accent, tokens.boost, tokens.kerbB, tokens.gold, tokens.kerbA];

  // Speed lines: thin streaks around the edge of the view, riding with the camera.
  const lineCount = tier.name === "high" ? 46 : 28;
  const lineGeometry = new PlaneGeometry(0.035, 2.4);
  lineGeometry.rotateX(Math.PI / 2);
  const lineMaterial = new MeshBasicMaterial({
    color: tokens.glow.clone().lerp(new Color(0xffffff), 0.6),
    transparent: true,
    opacity: 0,
    blending: AdditiveBlending,
    depthWrite: false,
    fog: false,
    toneMapped: false,
  });
  const lines = new InstancedMesh(lineGeometry, lineMaterial, lineCount);
  lines.frustumCulled = false;
  lines.instanceMatrix.setUsage(DynamicDrawUsage);
  const lineState = [];
  for (let i = 0; i < lineCount; i += 1) {
    lineState.push({ angle: rng() * Math.PI * 2, edge: rng.range(0.82, 1.15), z: -rng.range(3, 34), rate: rng.range(0.8, 1.4) });
  }
  const holder = new Object3D();
  holder.add(lines);

  const m = new Matrix4();
  const q = new Quaternion();
  const v = new Vector3();
  const s = new Vector3();
  const p = [0, 0, 0];
  const vel = [0, 0, 0];

  return {
    objects: [dust.points, sparks.points, confetti],
    cameraRig: holder,
    landing(point, frame, impact) {
      const n = Math.round((10 + Math.min(18, impact * 1.2)) * (tier.particles > 0.6 ? 1 : 0.6));
      for (let i = 0; i < n; i += 1) {
        const a = rng() * Math.PI * 2;
        const sp = rng.range(2, 6);
        const ca = Math.cos(a) * sp;
        const sa = Math.sin(a) * sp;
        for (let k = 0; k < 3; k += 1) {
          p[k] = point[k] - frame.n[k] * 0.45 + frame.r[k] * Math.cos(a) * 0.6 + frame.t[k] * Math.sin(a) * 0.6;
          vel[k] = frame.r[k] * ca + frame.t[k] * sa + frame.n[k] * rng.range(0.8, 2.2);
        }
        dust.emit(p, vel, rng.range(0.6, 1.0), rng.range(0.5, 0.9), rng.range(2.2, 3.4));
      }
    },
    boost(point, frame) {
      const n = Math.round(46 * (tier.particles > 0.6 ? 1 : 0.6));
      for (let i = 0; i < n; i += 1) {
        const back = rng.range(4, 13);
        const up = rng.range(2, 8);
        const side = rng.range(-4, 4);
        for (let k = 0; k < 3; k += 1) {
          p[k] = point[k] - frame.n[k] * 0.4;
          vel[k] = -frame.t[k] * back + frame.n[k] * up + frame.r[k] * side;
        }
        sparks.emit(p, vel, rng.range(0.35, 0.75), rng.range(0.14, 0.3), -0.2);
      }
    },
    finish(point, frame) {
      const colors = confettiColors();
      for (let i = 0; i < confettiCount; i += 1) {
        const o = i * 3;
        const side = rng() < 0.5 ? -1 : 1;
        for (let k = 0; k < 3; k += 1) {
          cPos[o + k] = point[k] + frame.n[k] * 7 + frame.r[k] * side * rng.range(2, 5);
          cVel[o + k] = frame.t[k] * rng.range(4, 14) + frame.n[k] * rng.range(3, 10) + frame.r[k] * -side * rng.range(0, 6);
        }
        cAngle[i] = rng() * Math.PI;
        cSpin[i] = rng.range(4, 12);
        cAge[i] = 0;
        confetti.setColorAt(i, colors[i % colors.length]);
      }
      if (confetti.instanceColor) confetti.instanceColor.needsUpdate = true;
      confettiLive = true;
    },
    clearConfetti() {
      for (let i = 0; i < confettiCount; i += 1) {
        cAge[i] = 99;
        confetti.setMatrixAt(i, zero);
      }
      confetti.instanceMatrix.needsUpdate = true;
      confettiLive = false;
    },
    // speedFactor: 0 below 80% of top speed, rising to 1 at top speed.
    update(dt, camera, speedFactor, speed) {
      dust.update(dt);
      sparks.update(dt);
      if (confettiLive) {
        let any = false;
        for (let i = 0; i < confettiCount; i += 1) {
          if (cAge[i] > 4) continue;
          any = true;
          cAge[i] += dt;
          const o = i * 3;
          cVel[o + 1] -= 9 * dt;
          const d = Math.exp(-1.6 * dt);
          cVel[o] *= d;
          cVel[o + 1] *= d;
          cVel[o + 2] *= d;
          cPos[o] += cVel[o] * dt;
          cPos[o + 1] += cVel[o + 1] * dt;
          cPos[o + 2] += cVel[o + 2] * dt;
          cAngle[i] += cSpin[i] * dt;
          q.setFromAxisAngle(cAxis[i], cAngle[i]);
          const fade = cAge[i] > 3.4 ? Math.max(0, 1 - (cAge[i] - 3.4) / 0.6) : 1;
          m.compose(v.set(cPos[o], cPos[o + 1], cPos[o + 2]), q, s.set(fade, fade, fade));
          confetti.setMatrixAt(i, m);
        }
        confetti.instanceMatrix.needsUpdate = true;
        confettiLive = any;
      }
      holder.position.copy(camera.position);
      holder.quaternion.copy(camera.quaternion);
      lineMaterial.opacity = Math.min(0.55, speedFactor * 0.55);
      lines.visible = speedFactor > 0.01;
      if (lines.visible) {
        const tanHalf = Math.tan((camera.fov * Math.PI) / 360);
        for (let i = 0; i < lineCount; i += 1) {
          const st = lineState[i];
          st.z += speed * st.rate * 1.6 * dt;
          if (st.z > -2.5) {
            st.z = -rng.range(26, 34);
            st.angle = rng() * Math.PI * 2;
          }
          const r = -st.z * tanHalf * st.edge;
          const x = Math.cos(st.angle) * r * camera.aspect;
          const y = Math.sin(st.angle) * r;
          m.makeTranslation(x, y, st.z);
          lines.setMatrixAt(i, m);
        }
        lines.instanceMatrix.needsUpdate = true;
      }
    },
    applyColors(t) {
      dust.material.uniforms.color.value.copy(t.floor).lerp(new Color(0xffffff), 0.35);
      sparks.material.uniforms.color.value.copy(t.boost).lerp(new Color(0xffffff), 0.35);
      lineMaterial.color.copy(t.glow).lerp(new Color(0xffffff), 0.6);
    },
  };
}
