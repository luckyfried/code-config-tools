// The storm sky: a dome with scrolling clouds and a bright slot at the horizon, lightning as a jagged Line2 bolt with
// a branch, a flash that lights the clouds and the ground, and rain streaks in a box that travels with the camera.
import * as THREE from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { NOISE } from "./glsl.js";

export const MAX_RAIN = 2200;

export function createSky({ tokens, rain, reducedMotion }) {
  const group = new THREE.Group();
  const uniforms = {
    uZenith: { value: new THREE.Color() },
    uHorizon: { value: new THREE.Color() },
    uBand: { value: new THREE.Color() },
    uBandStrength: { value: 1 },
    uCloudDark: { value: new THREE.Color() },
    uCloudLight: { value: new THREE.Color() },
    uCover: { value: 0.9 },
    uBolt: { value: new THREE.Color() },
    uFlash: { value: 0 },
    uFlashDir: { value: new THREE.Vector3(0, 0.3, -1).normalize() },
    uTime: { value: 0 },
    uSunDir: { value: new THREE.Vector3(0.5, 0.4, -0.6).normalize() },
  };
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(460, 48, 24),
    new THREE.ShaderMaterial({
      uniforms,
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          vDir = position;
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = p.xyww;
        }`,
      fragmentShader: /* glsl */ `
        ${NOISE}
        uniform vec3 uZenith;
        uniform vec3 uHorizon;
        uniform vec3 uBand;
        uniform float uBandStrength;
        uniform vec3 uCloudDark;
        uniform vec3 uCloudLight;
        uniform float uCover;
        uniform vec3 uBolt;
        uniform float uFlash;
        uniform vec3 uFlashDir;
        uniform vec3 uSunDir;
        uniform float uTime;
        varying vec3 vDir;
        void main() {
          vec3 d = normalize(vDir);
          float up = d.y;
          vec3 col = mix(uHorizon, uZenith, smoothstep(-0.03, 0.55, up));
          float sunSide = pow(max(dot(normalize(d.xz + 0.0001), normalize(uSunDir.xz + 0.0001)), 0.0), 2.0);
          float band = exp(-abs(up - 0.015) * 22.0) * uBandStrength * (0.35 + 0.65 * sunSide);
          col = mix(col, uBand, clamp(band, 0.0, 1.0));
          vec2 p = d.xz / (max(up, 0.0) + 0.09);
          float c = tt_fbm(vec3(p * 0.9 + vec2(uTime * 0.025, uTime * 0.012), uTime * 0.02));
          float c2 = tt_fbm(vec3(p * 2.4 - vec2(uTime * 0.04, 0.0), 3.0 + uTime * 0.03));
          float cov = smoothstep(0.32, 0.7, c * 0.75 + c2 * 0.35) * smoothstep(0.0, 0.12, up) * uCover;
          vec3 cloud = mix(uCloudDark, uCloudLight, smoothstep(0.35, 0.85, c2) * (0.4 + 0.6 * sunSide));
          col = mix(col, cloud, cov);
          float toward = pow(max(dot(d, uFlashDir), 0.0), 5.0);
          col += uBolt * uFlash * (0.05 + 0.6 * toward) * (0.3 + cov * 0.7);
          gl_FragColor = vec4(col, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
      side: THREE.BackSide,
      depthWrite: false,
    }),
  );
  dome.renderOrder = -10;
  dome.frustumCulled = false;
  group.add(dome);

  // Lightning: a main bolt and one branch, rebuilt for every strike.
  const boltMaterial = new LineMaterial({ color: 0xffffff, linewidth: 3.2, transparent: true, depthWrite: false });
  const branchMaterial = new LineMaterial({ color: 0xffffff, linewidth: 1.8, transparent: true, depthWrite: false });
  const bolt = new Line2(new LineGeometry(), boltMaterial);
  const branch = new Line2(new LineGeometry(), branchMaterial);
  for (const line of [bolt, branch]) {
    line.visible = false;
    line.frustumCulled = false;
    line.renderOrder = 8;
    group.add(line);
  }
  const strikeLight = new THREE.PointLight(0xffffff, 0, 140, 1.2);
  strikeLight.position.set(0, 30, 0);
  group.add(strikeLight);

  // Rain: thin quads that face the camera around their own fall line.
  const quad = new THREE.PlaneGeometry(1, 1);
  quad.translate(0, 0.5, 0);
  const rainGeometry = new THREE.InstancedBufferGeometry();
  rainGeometry.index = quad.index;
  rainGeometry.setAttribute("position", quad.getAttribute("position"));
  const offsets = new Float32Array(MAX_RAIN * 4);
  let seed = 98765;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < MAX_RAIN * 4; i++) offsets[i] = rnd();
  rainGeometry.setAttribute("aOff", new THREE.InstancedBufferAttribute(offsets, 4));
  rainGeometry.instanceCount = rain;
  const rainUniforms = {
    uCenter: { value: new THREE.Vector3() },
    uTime: uniforms.uTime,
    uRain: { value: new THREE.Color() },
    uAlpha: { value: 0.2 },
    uFlash: uniforms.uFlash,
    uWind: { value: new THREE.Vector2(4, 1.5) },
  };
  const rainMesh = new THREE.Mesh(
    rainGeometry,
    new THREE.ShaderMaterial({
      uniforms: { ...rainUniforms, ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog) },
      vertexShader: /* glsl */ `
        attribute vec4 aOff;
        uniform vec3 uCenter;
        uniform float uTime;
        uniform vec2 uWind;
        varying float vY;
        varying float vA;
        #include <fog_pars_vertex>
        void main() {
          vec3 box = vec3(56.0, 34.0, 56.0);
          float spd = 24.0 + aOff.w * 10.0;
          vec3 fall = vec3(uWind.x, -spd, uWind.y) * uTime;
          vec3 w = uCenter + (fract(aOff.xyz + fall / box - uCenter / box + 0.5) - 0.5) * box;
          w.y += box.y * 0.5 - 4.0;
          vec3 up = normalize(vec3(-uWind.x, spd, -uWind.y));
          vec3 toCam = normalize(cameraPosition - w);
          vec3 right = normalize(cross(up, toCam));
          float len = 1.1 + aOff.w * 0.9;
          vec3 wp = w + right * (position.x * 0.028) + up * (position.y * len);
          vY = position.y;
          vA = smoothstep(0.0, 0.15, w.y) * (0.6 + 0.4 * aOff.x) * smoothstep(5.0, 14.0, distance(w, cameraPosition));
          vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          #include <fog_vertex>
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uRain;
        uniform float uAlpha;
        uniform float uFlash;
        varying float vY;
        varying float vA;
        #include <fog_pars_fragment>
        void main() {
          float a = vY * vA * uAlpha * (1.0 + uFlash * 0.6);
          gl_FragColor = vec4(uRain * (0.85 + uFlash * 0.3), a);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
          #include <fog_fragment>
        }`,
      transparent: true,
      depthWrite: false,
      fog: true,
    }),
  );
  rainMesh.frustumCulled = false;
  rainMesh.renderOrder = 7;
  rainMesh.visible = rain > 0;
  group.add(rainMesh);

  const boltColor = new THREE.Color();
  const flashLight = new THREE.Color();
  let strikeAge = 99;
  const strikeTarget = new THREE.Vector3();

  const jag = (a, b, depth, spread, out) => {
    if (depth === 0) {
      out.push(b.x, b.y, b.z);
      return;
    }
    const mid = a.clone().lerp(b, 0.45 + Math.random() * 0.1);
    const len = a.distanceTo(b);
    mid.x += (Math.random() - 0.5) * len * spread;
    mid.z += (Math.random() - 0.5) * len * spread;
    mid.y += (Math.random() - 0.5) * len * spread * 0.2;
    jag(a, mid, depth - 1, spread, out);
    jag(mid, b, depth - 1, spread, out);
  };

  // A strobe of three return strokes, or a single slow swell when the person asks for less motion.
  const envelope = (t) => {
    if (reducedMotion) return t < 0.9 ? Math.sin((t / 0.9) * Math.PI) * 0.45 : 0;
    if (t < 0.06) return 1;
    if (t < 0.1) return 0.15;
    if (t < 0.17) return 0.75;
    if (t < 0.22) return 0.2;
    if (t < 0.4) return 0.95 - (t - 0.22) * 1.5;
    if (t < 0.85) return Math.max(0, 0.6 * (1 - (t - 0.4) / 0.45)) * 0.5;
    return 0;
  };

  const api = {
    group,
    uniforms,
    strikeLight,
    flash: 0,
    applyTokens(t) {
      uniforms.uZenith.value.copy(t.colors.skyZenith);
      uniforms.uHorizon.value.copy(t.colors.skyHorizon);
      uniforms.uBand.value.copy(t.colors.skyBand);
      uniforms.uBandStrength.value = t.numbers.skyBandStrength;
      uniforms.uCloudDark.value.copy(t.colors.cloudDark);
      uniforms.uCloudLight.value.copy(t.colors.cloudLight);
      uniforms.uCover.value = t.numbers.cloudCover;
      uniforms.uBolt.value.copy(t.colors.bolt);
      rainUniforms.uRain.value.copy(t.colors.rain);
      rainUniforms.uAlpha.value = t.numbers.rainAlpha;
      boltColor.copy(t.colors.bolt);
      flashLight.copy(t.colors.flashLight);
      strikeLight.color.copy(flashLight);
    },
    setRain(n) {
      rainGeometry.instanceCount = Math.min(n, MAX_RAIN);
      rainMesh.visible = n > 0;
    },
    setResolution(w, h) {
      boltMaterial.resolution.set(w, h);
      branchMaterial.resolution.set(w, h);
    },
    setSun(dir) {
      uniforms.uSunDir.value.copy(dir);
    },
    // Strike the ground at `target`; the bolt drops from the cloud base above and a little behind it.
    strike(target, cameraPos) {
      strikeTarget.copy(target);
      const top = new THREE.Vector3(target.x + (Math.random() - 0.5) * 18, 62 + Math.random() * 10, target.z + (Math.random() - 0.5) * 18);
      const points = [top.x, top.y, top.z];
      jag(top, target, 6, 0.32, points);
      bolt.geometry.dispose();
      bolt.geometry = new LineGeometry();
      bolt.geometry.setPositions(points);
      bolt.computeLineDistances();
      const pick = 12 + Math.floor(Math.random() * 20);
      const from = new THREE.Vector3(points[pick * 3], points[pick * 3 + 1], points[pick * 3 + 2]);
      const to = from.clone().add(new THREE.Vector3((Math.random() - 0.5) * 30, -from.y * (0.35 + Math.random() * 0.3), (Math.random() - 0.5) * 30));
      const bp = [from.x, from.y, from.z];
      jag(from, to, 5, 0.4, bp);
      branch.geometry.dispose();
      branch.geometry = new LineGeometry();
      branch.geometry.setPositions(bp);
      strikeLight.position.set(target.x, 18, target.z);
      uniforms.uFlashDir.value.copy(top).sub(cameraPos).normalize();
      strikeAge = 0;
    },
    update(dt, time, cameraPos, center) {
      uniforms.uTime.value = time;
      dome.position.copy(cameraPos);
      rainUniforms.uCenter.value.copy(center);
      strikeAge += dt;
      const f = envelope(strikeAge);
      api.flash = f;
      uniforms.uFlash.value = f;
      const on = f > 0.04;
      bolt.visible = on;
      branch.visible = on && strikeAge < 0.3;
      const boost = reducedMotion ? 2.2 : 5.5;
      boltMaterial.color.copy(boltColor).multiplyScalar(boost * f + 0.2);
      boltMaterial.opacity = Math.min(1, f * 1.6);
      branchMaterial.color.copy(boltColor).multiplyScalar(boost * 0.8 * f);
      branchMaterial.opacity = Math.min(1, f * 1.4);
      strikeLight.intensity = f * 110;
      return f;
    },
    get strikeAge() {
      return strikeAge;
    },
    get strikePoint() {
      return strikeTarget;
    },
  };
  api.applyTokens(tokens);
  return api;
}
