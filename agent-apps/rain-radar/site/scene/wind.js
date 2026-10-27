// Wind: a few thousand particles carried by the 7 by 7 forecast grid, each drawing a short line into a map-sized
// trail picture that fades a little every frame. The ground shader lays that picture over the map.
import * as THREE from "three";

const SPEED = 0.0062; // map widths a second for each meter a second of wind

const fadeMaterial = () =>
  new THREE.ShaderMaterial({
    uniforms: { uPrev: { value: null } },
    vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: `uniform sampler2D uPrev; varying vec2 vUv;
      void main() { vec4 p = texture2D(uPrev, vUv); gl_FragColor = max(p * 0.935 - 1.5 / 255.0, 0.0); }`,
    depthTest: false,
    depthWrite: false,
  });

const lineMaterial = () =>
  new THREE.ShaderMaterial({
    vertexShader: `attribute float aGlow; varying float vGlow;
      void main() { vGlow = aGlow; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: `varying float vGlow; void main() { gl_FragColor = vec4(vGlow, vGlow, vGlow, 1.0); }`,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    depthWrite: false,
    transparent: true,
  });

export function createWind(renderer, tier) {
  const opts = { type: THREE.UnsignedByteType, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false };
  const size = tier.trail;
  const targets = [new THREE.WebGLRenderTarget(size, size, opts), new THREE.WebGLRenderTarget(size, size, opts)];
  let current = 0;

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const fade = fadeMaterial();
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), fade);
  quad.frustumCulled = false;
  const fadeScene = new THREE.Scene();
  fadeScene.add(quad);

  const max = 3500;
  const pos = new Float32Array(max * 2 * 3);
  const glow = new Float32Array(max * 2);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  geometry.setAttribute("aGlow", new THREE.BufferAttribute(glow, 1).setUsage(THREE.DynamicDrawUsage));
  const lines = new THREE.LineSegments(geometry, lineMaterial());
  lines.frustumCulled = false;
  const lineScene = new THREE.Scene();
  lineScene.add(lines);

  const px = new Float32Array(max);
  const py = new Float32Array(max);
  const age = new Float32Array(max);
  const life = new Float32Array(max);
  let u = new Float32Array(49);
  let v = new Float32Array(49);
  let box = { x0: 0, y0: 0, x1: 1, y1: 1 };
  let count = tier.particles;
  let rand = 1;
  const random = () => {
    rand = (rand * 16807) % 2147483647;
    return (rand - 1) / 2147483646;
  };

  const spawn = (i, anyAge) => {
    px[i] = box.x0 + random() * (box.x1 - box.x0);
    py[i] = box.y0 + random() * (box.y1 - box.y0);
    life[i] = 1.6 + random() * 3.2;
    age[i] = anyAge ? random() * life[i] : 0;
  };
  for (let i = 0; i < max; i++) spawn(i, true);

  // wind at a uv spot, bilinear across the grid's cell centers; returns map widths a second (y south)
  const sample = (x, y, out) => {
    const gx = Math.max(0, Math.min(6, x * 7 - 0.5));
    const gy = Math.max(0, Math.min(6, y * 7 - 0.5));
    const i0 = Math.min(5, Math.floor(gx));
    const j0 = Math.min(5, Math.floor(gy));
    const fx = gx - i0;
    const fy = gy - j0;
    const k = j0 * 7 + i0;
    const lerp2 = (a) => (a[k] * (1 - fx) + a[k + 1] * fx) * (1 - fy) + (a[k + 7] * (1 - fx) + a[k + 8] * fx) * fy;
    out[0] = lerp2(u) * SPEED;
    out[1] = -lerp2(v) * SPEED;
  };

  const vel = [0, 0];
  const wind = {
    get texture() {
      return targets[current].texture;
    },
    setField(nu, nv) {
      u = nu;
      v = nv;
    },
    setBox(b) {
      box = b;
    },
    setTier(t) {
      count = Math.min(max, t.particles);
    },
    clear() {
      for (const t of targets) {
        renderer.setRenderTarget(t);
        renderer.clear();
      }
      renderer.setRenderTarget(null);
    },
    step(dt, active) {
      dt = Math.min(dt, 1 / 20);
      for (let i = 0; i < max; i++) {
        const o = i * 6;
        if (i >= count || !active) {
          glow[i * 2] = glow[i * 2 + 1] = 0;
          pos[o] = pos[o + 3] = -2;
          continue;
        }
        const x = px[i];
        const y = py[i];
        sample(x, y, vel);
        const nx = x + vel[0] * dt;
        const ny = y + vel[1] * dt;
        age[i] += dt;
        if (age[i] > life[i] || nx < box.x0 || nx > box.x1 || ny < box.y0 || ny > box.y1) {
          spawn(i, false);
          glow[i * 2] = glow[i * 2 + 1] = 0;
          pos[o] = pos[o + 3] = -2;
          continue;
        }
        const a = age[i];
        const fadeIn = Math.min(1, a / 0.5);
        const fadeOut = Math.min(1, (life[i] - a) / 0.6);
        const speed = Math.hypot(vel[0], vel[1]) / SPEED;
        const g = fadeIn * fadeOut * (0.5 + 0.5 * Math.min(1, speed / 9));
        pos[o] = x * 2 - 1;
        pos[o + 1] = y * 2 - 1;
        pos[o + 3] = nx * 2 - 1;
        pos[o + 4] = ny * 2 - 1;
        glow[i * 2] = g * 0.75;
        glow[i * 2 + 1] = g;
        px[i] = nx;
        py[i] = ny;
      }
      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.aGlow.needsUpdate = true;

      const prev = targets[current];
      current = 1 - current;
      const next = targets[current];
      const auto = renderer.autoClear;
      renderer.autoClear = false;
      renderer.setRenderTarget(next);
      fade.uniforms.uPrev.value = prev.texture;
      renderer.render(fadeScene, camera);
      if (active) renderer.render(lineScene, camera);
      renderer.setRenderTarget(null);
      renderer.autoClear = auto;
    },
    dispose() {
      for (const t of targets) t.dispose();
    },
  };
  return wind;
}
