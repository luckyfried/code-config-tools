// Sparks: bright points that streak off a lifted car and burst where something heavy lands. Their color is pushed
// past white so the bloom catches them.
import * as THREE from "three";

const MAX = 480;

export function createSparks(tokens) {
  const positions = new Float32Array(MAX * 3);
  const life = new Float32Array(MAX);
  const velocity = new Float32Array(MAX * 3);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage));
  geometry.setAttribute("aLife", new THREE.BufferAttribute(life, 1).setUsage(THREE.DynamicDrawUsage));
  const uniforms = { uColor: { value: new THREE.Color() }, uPx: { value: 600 } };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */ `
      attribute float aLife;
      uniform float uPx;
      varying float vLife;
      void main() {
        vLife = aLife;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = aLife > 0.0 ? uPx * (0.1 + 0.12 * aLife) / max(-mv.z, 0.5) : 0.0;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying float vLife;
      void main() {
        if (vLife <= 0.0) discard;
        float d = length(gl_PointCoord - 0.5) * 2.0;
        if (d > 1.0) discard;
        float a = (1.0 - smoothstep(0.0, 1.0, d)) * min(1.0, vLife * 3.0);
        gl_FragColor = vec4(uColor * (2.0 + 5.0 * vLife) * a, a);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = 9;
  let next = 0;
  let alive = 0;

  return {
    points,
    applyTokens(t) {
      uniforms.uColor.value.copy(t.colors.spark);
    },
    setPxScale(v) {
      uniforms.uPx.value = v;
    },
    emit(x, y, z, count, speed, vx = 0, vy = 0, vz = 0) {
      for (let k = 0; k < count; k++) {
        const i = next;
        next = (next + 1) % MAX;
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = z;
        const a = Math.random() * Math.PI * 2;
        const u = Math.random() * 2 - 1;
        const r = Math.sqrt(1 - u * u);
        velocity[i * 3] = vx + Math.cos(a) * r * speed;
        velocity[i * 3 + 1] = vy + Math.abs(u) * speed;
        velocity[i * 3 + 2] = vz + Math.sin(a) * r * speed;
        life[i] = 0.6 + Math.random() * 0.4;
      }
      alive = MAX;
    },
    update(dt) {
      if (alive <= 0) return;
      let any = 0;
      for (let i = 0; i < MAX; i++) {
        if (life[i] <= 0) continue;
        life[i] -= dt * 1.6;
        velocity[i * 3 + 1] -= 14 * dt;
        positions[i * 3] += velocity[i * 3] * dt;
        positions[i * 3 + 1] += velocity[i * 3 + 1] * dt;
        positions[i * 3 + 2] += velocity[i * 3 + 2] * dt;
        if (positions[i * 3 + 1] < 0.05) {
          positions[i * 3 + 1] = 0.05;
          velocity[i * 3 + 1] *= -0.3;
          velocity[i * 3] *= 0.6;
          velocity[i * 3 + 2] *= 0.6;
        }
        any++;
      }
      alive = any;
      geometry.getAttribute("position").needsUpdate = true;
      geometry.getAttribute("aLife").needsUpdate = true;
    },
  };
}
