// Dust motes drifting in front of the shelf. They glow where they cross the key light's cone and fade outside it.
// The drift runs in the vertex shader, so the motes cost nothing on the main thread.
import * as THREE from "three";

const vertex = /* glsl */ `
  attribute float aSeed;
  uniform float uTime;
  uniform float uScale;
  uniform vec3 uKeyPos;
  uniform vec3 uKeyDir;
  uniform float uCosOuter;
  uniform float uCosInner;
  uniform vec3 uBoxMin;
  uniform vec3 uBoxSize;
  varying float vLight;
  varying float vTwinkle;
  void main() {
    vec3 p = position;
    float t = uTime * (0.35 + aSeed * 0.4);
    p.x += sin(t * 0.21 + aSeed * 31.0) * 0.07 + uTime * 0.004 * (aSeed - 0.5);
    p.y = uBoxMin.y + mod(position.y - uBoxMin.y - uTime * (0.006 + aSeed * 0.012), uBoxSize.y) + sin(t * 0.13 + aSeed * 9.0) * 0.03;
    p.z += cos(t * 0.17 + aSeed * 17.0) * 0.05;
    p.x = uBoxMin.x + mod(p.x - uBoxMin.x, uBoxSize.x);
    vec3 toP = normalize(p - uKeyPos);
    float c = dot(toP, uKeyDir);
    vLight = smoothstep(uCosOuter, uCosInner, c);
    vTwinkle = 0.65 + 0.35 * sin(uTime * (1.3 + aSeed * 2.0) + aSeed * 40.0);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uScale * (0.6 + aSeed * 1.1) / -mv.z;
  }
`;

const fragment = /* glsl */ `
  uniform vec3 uColor;
  uniform float uPower;
  varying float vLight;
  varying float vTwinkle;
  void main() {
    vec2 d = gl_PointCoord - 0.5;
    float r = length(d);
    float a = smoothstep(0.5, 0.0, r);
    a *= a;
    float glow = (0.08 + vLight * 0.92) * vTwinkle * uPower;
    gl_FragColor = vec4(uColor * glow * a, 1.0);
  }
`;

export function createMotes(count, tokens) {
  const boxMin = new THREE.Vector3(-1.6, 0.05, 0.08);
  const boxSize = new THREE.Vector3(3.2, 1.45, 1.35);
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  let s = 1234567;
  const rand = () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
  for (let i = 0; i < count; i += 1) {
    positions[i * 3] = boxMin.x + rand() * boxSize.x;
    positions[i * 3 + 1] = boxMin.y + rand() * boxSize.y;
    positions[i * 3 + 2] = boxMin.z + rand() * boxSize.z;
    seeds[i] = rand();
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
  const material = new THREE.ShaderMaterial({
    vertexShader: vertex,
    fragmentShader: fragment,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uTime: { value: 0 },
      uScale: { value: 40 },
      uKeyPos: { value: new THREE.Vector3() },
      uKeyDir: { value: new THREE.Vector3(0, -1, 0) },
      uCosOuter: { value: Math.cos(0.5) },
      uCosInner: { value: Math.cos(0.3) },
      uBoxMin: { value: boxMin },
      uBoxSize: { value: boxSize },
      uColor: { value: new THREE.Color(tokens.mote) },
      uPower: { value: tokens.motePower },
    },
  });
  const points = new THREE.Points(geo, material);
  points.frustumCulled = false;
  points.renderOrder = 5;

  return {
    points,
    place(geo2, center) {
      boxMin.set(center.x - Math.max(1.6, geo2.outerW / 2 + 0.5), 0.05, 0.08);
      boxSize.set(Math.max(3.2, geo2.outerW + 1), geo2.height + 0.3, 1.35);
    },
    aim(key) {
      material.uniforms.uKeyPos.value.copy(key.position);
      material.uniforms.uKeyDir.value.copy(key.target.position).sub(key.position).normalize();
      material.uniforms.uCosOuter.value = Math.cos(key.angle);
      material.uniforms.uCosInner.value = Math.cos(key.angle * (1 - key.penumbra * 0.8));
    },
    resize(heightPx, pixelRatio, fov) {
      material.uniforms.uScale.value = (heightPx * pixelRatio * 0.0028) / Math.tan((fov * Math.PI) / 360);
    },
    apply(t) {
      material.uniforms.uColor.value.set(t.mote);
      material.uniforms.uPower.value = t.motePower;
    },
    tick(time) {
      material.uniforms.uTime.value = time;
    },
  };
}
