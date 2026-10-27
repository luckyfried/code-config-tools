// The sky dome: a three-band gradient from the theme, a sun (or a moon) with its halo, lit streaks of cloud,
// and stars when the theme asks for them. It follows the camera, so it never ends.
import * as THREE from "three";

const vertex = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_Position = p.xyww;
  }
`;

const fragment = /* glsl */ `
  uniform vec3 uZenith;
  uniform vec3 uMid;
  uniform vec3 uHorizon;
  uniform vec3 uSun;
  uniform vec3 uGlow;
  uniform vec3 uCloud;
  uniform vec3 uSunDir;
  uniform float uSunSize;
  uniform float uStars;
  uniform float uMoon;
  uniform float uTime;
  varying vec3 vDir;

  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p); vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
  }
  float fbm(vec2 p) {
    float v = 0.0; float a = 0.5;
    for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
    return v;
  }

  void main() {
    vec3 d = normalize(vDir);
    float h = d.y;
    vec3 col = mix(uHorizon, uMid, smoothstep(-0.02, 0.16, h));
    col = mix(col, uZenith, smoothstep(0.12, 0.62, h));
    // below the horizon the desert haze takes over
    col = mix(col, uHorizon * 0.92, smoothstep(0.0, -0.08, h));

    float sd = max(dot(d, uSunDir), 0.0);
    float glowWide = pow(sd, 6.0) * 0.55;
    float glowTight = pow(sd, 90.0) * 1.1;
    col += uGlow * (glowWide + glowTight) * (1.0 - 0.6 * uMoon);
    col += uGlow * pow(sd, 18.0) * 0.4 * uMoon;

    // stratus streaks, lit from the sun side
    float band = smoothstep(0.015, 0.06, h) * (1.0 - smoothstep(0.18, 0.42, h));
    vec2 cp = d.xz / (h + 0.11);
    float n = fbm(vec2(cp.x * 0.55 + uTime * 0.004, cp.y * 2.6));
    float streak = smoothstep(0.52, 0.8, n) * band;
    vec3 cloudLit = mix(uCloud * 0.55, uCloud * 1.35, pow(sd, 3.0));
    col = mix(col, cloudLit, streak * 0.75);

    // the disk: a sun is hot and soft-edged; a moon is cool with a few darker seas
    float cosR = cos(radians(uSunSize) * 0.5);
    float disk = smoothstep(cosR - 0.00012, cosR + 0.00006, dot(d, uSunDir));
    vec3 diskColor = uSun * mix(5.5, 2.2, uMoon);
    if (uMoon > 0.5) {
      vec3 side = normalize(cross(uSunDir, vec3(0.0, 1.0, 0.0)));
      vec3 up = cross(side, uSunDir);
      vec2 mp = vec2(dot(d, side), dot(d, up)) * 160.0;
      diskColor *= 0.82 + 0.18 * smoothstep(0.35, 0.65, fbm(mp));
    }
    col = mix(col, diskColor, disk * (1.0 - streak * 0.6));

    // stars, only above the haze
    if (uStars > 0.0) {
      vec2 sp = vec2(atan(d.z, d.x) * 180.0, h * 240.0);
      vec2 cell = floor(sp);
      float r = hash(cell);
      float star = step(0.985, r) * smoothstep(0.08, 0.3, h);
      float tw = 0.65 + 0.35 * sin(uTime * (1.5 + r * 3.0) + r * 40.0);
      vec2 fp = fract(sp) - 0.5;
      star *= smoothstep(0.32, 0.0, length(fp));
      col += vec3(0.9, 0.95, 1.0) * star * tw * uStars * 1.6;
    }
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export function sunDirection(tokens) {
  const el = THREE.MathUtils.degToRad(tokens.sunElevation);
  const az = THREE.MathUtils.degToRad(tokens.sunAzimuth);
  // azimuth 0 is straight down the street (-z); positive swings right (+x)
  return new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)).normalize();
}

export function createSky(tokens) {
  const uniforms = {
    uZenith: { value: new THREE.Color() },
    uMid: { value: new THREE.Color() },
    uHorizon: { value: new THREE.Color() },
    uSun: { value: new THREE.Color() },
    uGlow: { value: new THREE.Color() },
    uCloud: { value: new THREE.Color() },
    uSunDir: { value: new THREE.Vector3() },
    uSunSize: { value: 2 },
    uStars: { value: 0 },
    uMoon: { value: 0 },
    uTime: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: vertex,
    fragmentShader: fragment,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(900, 48, 24), material);
  mesh.name = "sky";
  mesh.frustumCulled = false;
  mesh.renderOrder = -10;

  function apply(t) {
    uniforms.uZenith.value.copy(t.skyZenith);
    uniforms.uMid.value.copy(t.skyMid);
    uniforms.uHorizon.value.copy(t.skyHorizon);
    uniforms.uSun.value.copy(t.sun);
    uniforms.uGlow.value.copy(t.sunGlow);
    uniforms.uCloud.value.copy(t.cloud);
    uniforms.uSunDir.value.copy(sunDirection(t));
    uniforms.uSunSize.value = t.sunSize;
    uniforms.uStars.value = t.stars;
    uniforms.uMoon.value = t.moon;
  }
  apply(tokens);

  return {
    mesh,
    apply,
    update(time, camera) {
      uniforms.uTime.value = time;
      mesh.position.copy(camera.position);
    },
  };
}
