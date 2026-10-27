// The funnel: two twisted noise shells and a faint haze shell, the wall cloud it hangs from, the debris chips that
// orbit it (animated wholly in the vertex shader from one time uniform), and the dust ring churning at its base.
import * as THREE from "three";
import { NOISE, FUNNEL_SHAPE, ROTATE } from "./glsl.js";

export const MAX_CHIPS = 3000;
const DUST = 520;

// The funnel's size at growth 0 (a fresh storm) and 1 (barn-eater).
export function funnelSize(growth) {
  return {
    height: 14 + 18 * growth,
    rBottom: 0.75 + 2.0 * growth,
    rTop: 5.0 + 8.0 * growth,
    reach: 2.3 + 4.6 * growth,
  };
}

export function createFunnel({ tokens, chips }) {
  const shape = {
    uFunnelPos: { value: new THREE.Vector3() },
    uHeight: { value: 14 },
    uRBottom: { value: 0.75 },
    uRTop: { value: 5 },
    uSway: { value: 1.2 },
    uLean: { value: new THREE.Vector2() },
    uTime: { value: 0 },
  };
  const look = {
    uColTop: { value: new THREE.Color() },
    uColBottom: { value: new THREE.Color() },
    uGlowCol: { value: new THREE.Color() },
    uFlash: { value: 0 },
    uSunDir: { value: new THREE.Vector3(0.4, 0.6, 0.3) },
    uSunCol: { value: new THREE.Color(1, 1, 1) },
    uSkyCol: { value: new THREE.Color(1, 1, 1) },
    uGroundCol: { value: new THREE.Color(0.3, 0.3, 0.3) },
    uSpinBoost: { value: 0 },
    uCloudDark: { value: new THREE.Color() },
    uFunnelLight: { value: 0 },
    uFlick: { value: 0 },
  };
  const group = new THREE.Group();

  const shell = (layerScale, opacity, spin, order, darken) => {
    const geometry = new THREE.CylinderGeometry(1, 1, 1, 64, 48, true);
    geometry.translate(0, 0.5, 0);
    const material = new THREE.ShaderMaterial({
      uniforms: {
        ...shape, ...look, ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
        uLayerScale: { value: layerScale }, uOpacity: { value: opacity }, uSpin: { value: spin }, uDarken: { value: darken },
        uBaseOpacity: { value: opacity },
      },
      vertexShader: /* glsl */ `
        ${FUNNEL_SHAPE}
        uniform float uLayerScale;
        varying float vH;
        varying vec2 vDir;
        varying vec3 vWorld;
        varying vec3 vNormalW;
        #include <fog_pars_vertex>
        void main() {
          float h = position.y;
          float ang = atan(position.z, position.x);
          float r = funnelRadius(h) * uLayerScale;
          r *= 1.0 + 0.07 * sin(ang * 3.0 + h * 9.0 - uTime * 5.0) + 0.05 * sin(ang * 5.0 - h * 15.0 + uTime * 3.3);
          r += smoothstep(0.82, 1.0, h) * uRTop * 0.35;
          vec3 axis = funnelAxis(h);
          vec3 wp = axis + vec3(cos(ang) * r, 0.0, sin(ang) * r);
          vH = h;
          vDir = vec2(cos(ang), sin(ang));
          vWorld = wp;
          float slope = (uRTop - uRBottom) / max(uHeight, 0.001);
          vNormalW = normalize(vec3(cos(ang), -slope, sin(ang)));
          vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          #include <fog_vertex>
        }`,
      fragmentShader: /* glsl */ `
        ${NOISE}
        uniform float uTime;
        uniform float uHeight;
        uniform float uOpacity;
        uniform float uSpin;
        uniform float uDarken;
        uniform float uFlash;
        uniform float uSpinBoost;
        uniform float uFunnelLight;
        uniform float uFlick;
        uniform vec3 uColTop;
        uniform vec3 uColBottom;
        uniform vec3 uGlowCol;
        uniform vec3 uSunDir;
        uniform vec3 uSunCol;
        uniform vec3 uSkyCol;
        varying float vH;
        varying vec2 vDir;
        varying vec3 vWorld;
        varying vec3 vNormalW;
        #include <fog_pars_fragment>
        void main() {
          float a = atan(vDir.y, vDir.x) + vH * 4.0 - uTime * (uSpin + uSpinBoost);
          float z = vH * uHeight * 0.16;
          float n1 = tt_fbm(vec3(cos(a) * 1.6, sin(a) * 1.6, z - uTime * 0.7));
          float n2 = tt_fbm(vec3(cos(a * 2.0 + 1.3) * 2.6, sin(a * 2.0 + 1.3) * 2.6, z * 2.6 - uTime * 1.9));
          float n = n1 * 0.62 + n2 * 0.5;
          float dens = smoothstep(0.24, 0.6, n);
          vec3 V = normalize(cameraPosition - vWorld);
          float facing = abs(dot(normalize(vNormalW), V));
          float edge = smoothstep(0.02, 0.38, facing);
          float alpha = dens * edge * uOpacity;
          alpha *= smoothstep(0.0, 0.035, vH) * (1.0 - smoothstep(0.72, 0.97, vH));
          vec3 col = mix(uColBottom, uColTop, smoothstep(0.0, 0.85, vH));
          col *= (0.5 + 0.75 * n2) * uDarken;
          float lit = 0.5 + 0.5 * dot(normalize(vNormalW.xz + 0.0001), normalize(uSunDir.xz + 0.0001));
          col *= mix(vec3(0.62), uSunCol * 1.12, lit) * mix(vec3(1.0), uSkyCol, 0.25);
          col *= mix(0.55, 1.0, smoothstep(0.0, 0.3, vH));
          col += uGlowCol * uFunnelLight * (0.1 + 0.55 * pow(1.0 - facing, 2.0)) * (0.6 + 0.6 * n1);
          float glow = (uFlash + uFlick * 0.5) * pow(1.0 - n2, 2.2) * (0.35 + 0.65 * vH);
          col += uGlowCol * glow * 3.2;
          alpha = clamp(alpha + glow * 0.25 * edge, 0.0, 1.0);
          gl_FragColor = vec4(col, alpha);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
          #include <fog_fragment>
        }`,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      fog: true,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.frustumCulled = false;
    mesh.renderOrder = order;
    group.add(mesh);
    return mesh;
  };
  const inner = shell(0.62, 1.0, 2.4, 3, 0.8);
  const outer = shell(1.0, 0.92, 1.6, 4, 1.0);
  const haze = shell(1.45, 0.28, 0.9, 5, 1.15);

  // The wall cloud: a sagging disc of rotating cloud the funnel hangs from.
  const wallGeometry = new THREE.RingGeometry(0.0, 1, 72, 14);
  wallGeometry.rotateX(-Math.PI / 2);
  const wallMaterial = new THREE.ShaderMaterial({
    uniforms: { ...shape, ...look, ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog) },
    vertexShader: /* glsl */ `
      ${FUNNEL_SHAPE}
      varying vec2 vP;
      varying vec3 vWorld;
      varying vec3 vNormalW;
      #include <fog_pars_vertex>
      void main() {
        vec2 p = position.xz;
        float r = length(p);
        vec3 top = funnelAxis(1.0);
        float R = uRTop * 5.5;
        vec3 wp = top + vec3(p.x * R, -pow(1.0 - r, 2.0) * uRTop * 0.7 + r * r * uRTop * 0.6, p.y * R);
        float slope = (2.0 * (1.0 - r) * 0.7 + 2.0 * r * 0.6) * uRTop / R;
        vec2 dir = p / max(r, 0.0001);
        vNormalW = normalize(vec3(-slope * dir.x, 1.0, -slope * dir.y));
        vP = p;
        vWorld = wp;
        vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */ `
      ${NOISE}
      uniform float uTime;
      uniform float uFlash;
      uniform float uSpinBoost;
      uniform vec3 uColTop;
      uniform vec3 uCloudDark;
      uniform vec3 uGlowCol;
      uniform vec3 uSunCol;
      uniform float uFlick;
      varying vec2 vP;
      varying vec3 vWorld;
      varying vec3 vNormalW;
      #include <fog_pars_fragment>
      void main() {
        float r = length(vP);
        float a = atan(vP.y, vP.x) + uTime * (0.32 + uSpinBoost * 0.2) + (1.0 - r) * 2.2;
        float n = tt_fbm(vec3(cos(a) * r * 3.2, sin(a) * r * 3.2, uTime * 0.06));
        float m = tt_fbm(vec3(cos(a * 2.0) * r * 6.0, sin(a * 2.0) * r * 6.0, uTime * 0.11 + 4.0));
        float rim = r + (m - 0.5) * 0.35;
        float dens = smoothstep(0.22, 0.6, n * 0.7 + m * 0.4) * (1.0 - smoothstep(0.2, 0.85, rim));
        dens = max(dens, 1.0 - smoothstep(0.1, 0.32, rim));
        vec3 col = mix(uColTop * 0.8, uCloudDark, smoothstep(0.1, 0.8, r));
        col *= 0.75 + 0.5 * m;
        col *= mix(vec3(1.0), uSunCol, 0.2);
        col += uGlowCol * (uFlash + uFlick * 0.12) * (0.6 + m) * 1.4 * (1.0 - r);
        // A cloud deck seen edge-on thins out, so its silhouette never shows as a straight line.
        float facing = abs(dot(normalize(vNormalW), normalize(cameraPosition - vWorld)));
        dens *= smoothstep(0.03, 0.42, facing + (n - 0.5) * 0.25);
        gl_FragColor = vec4(col, dens * 0.96);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    fog: true,
  });
  const wall = new THREE.Mesh(wallGeometry, wallMaterial);
  wall.frustumCulled = false;
  wall.renderOrder = 6;
  group.add(wall);

  // Debris chips: every chip's radius, climb, height, and angular speed live in its attributes.
  const chipBase = new THREE.BoxGeometry(1, 0.2, 0.7);
  const chipGeometry = new THREE.InstancedBufferGeometry();
  chipGeometry.index = chipBase.index;
  chipGeometry.setAttribute("position", chipBase.getAttribute("position"));
  chipGeometry.setAttribute("normal", chipBase.getAttribute("normal"));
  const orbit = new Float32Array(MAX_CHIPS * 4);
  const extra = new Float32Array(MAX_CHIPS * 4);
  let s = 12345;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < MAX_CHIPS; i++) {
    const spray = rnd() < 0.2;
    orbit[i * 4] = spray ? 1.3 + rnd() * 0.9 : 0.8 + rnd() * 0.6;
    orbit[i * 4 + 1] = rnd();
    orbit[i * 4 + 2] = 0.6 + rnd() * 0.9;
    orbit[i * 4 + 3] = rnd();
    extra[i * 4] = (0.09 + Math.pow(rnd(), 3) * 0.42) * (spray ? 0.8 : 1);
    extra[i * 4 + 1] = spray ? 0.12 + rnd() * 0.25 : 0.55 + rnd() * 0.45;
    extra[i * 4 + 2] = Math.floor(rnd() * 3);
    extra[i * 4 + 3] = rnd();
  }
  chipGeometry.setAttribute("aOrbit", new THREE.InstancedBufferAttribute(orbit, 4));
  chipGeometry.setAttribute("aExtra", new THREE.InstancedBufferAttribute(extra, 4));
  chipGeometry.instanceCount = chips;
  const chipMaterial = new THREE.ShaderMaterial({
    uniforms: {
      ...shape, ...look, ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      uDebris: { value: [new THREE.Color(), new THREE.Color(), new THREE.Color()] },
      uSunI: { value: 1 }, uHemiI: { value: 1 },
    },
    vertexShader: /* glsl */ `
      ${FUNNEL_SHAPE}
      ${ROTATE}
      attribute vec4 aOrbit;
      attribute vec4 aExtra;
      uniform vec3 uDebris[3];
      uniform float uSpinBoost;
      varying vec3 vColor;
      varying vec3 vN;
      #include <fog_pars_vertex>
      void main() {
        float sp = aOrbit.z;
        float climb = fract(aOrbit.y + uTime * 0.07 * sp);
        float h = climb * aExtra.y;
        float ang = aOrbit.w * 6.2831 + uTime * sp * (3.4 - 2.2 * h) * (1.0 + uSpinBoost * 0.8);
        float r = funnelRadius(h) * aOrbit.x + 0.35;
        vec3 c = funnelAxis(h);
        float fade = smoothstep(0.0, 0.08, climb) * (1.0 - smoothstep(0.8, 1.0, climb));
        vec3 axisR = normalize(vec3(fract(aOrbit.w * 13.1) - 0.5, fract(aOrbit.w * 5.7) - 0.5, fract(aOrbit.w * 3.3) - 0.5) + 0.001);
        float ra = uTime * (2.0 + 5.0 * fract(aOrbit.w * 7.3));
        float size = aExtra.x * fade * (0.8 + uRBottom * 0.25);
        vec3 p = tt_rotate(position * size, axisR, ra);
        vN = tt_rotate(normal, axisR, ra);
        vec3 wp = c + vec3(cos(ang) * r, 0.0, sin(ang) * r) + p;
        int k = int(aExtra.z + 0.5);
        vColor = uDebris[k] * (0.75 + 0.5 * aExtra.w);
        vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uSunDir;
      uniform vec3 uSunCol;
      uniform vec3 uSkyCol;
      uniform vec3 uGroundCol;
      uniform vec3 uGlowCol;
      uniform float uFlash;
      uniform float uFunnelLight;
      uniform float uFlick;
      uniform float uSunI;
      uniform float uHemiI;
      varying vec3 vColor;
      varying vec3 vN;
      #include <fog_pars_fragment>
      void main() {
        vec3 n = normalize(vN);
        float diff = abs(dot(n, normalize(uSunDir)));
        vec3 hemi = mix(uGroundCol, uSkyCol, n.y * 0.5 + 0.5) * uHemiI * 0.32;
        vec3 col = vColor * (hemi + uSunCol * diff * uSunI * 0.3 + uGlowCol * (uFunnelLight * (0.45 + 0.4 * diff) + (uFlash + uFlick * 0.4) * 0.35));
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
    fog: true,
  });
  const debris = new THREE.Mesh(chipGeometry, chipMaterial);
  debris.frustumCulled = false;
  group.add(debris);

  // The dust ring: soft points churning around the base.
  const dustGeometry = new THREE.BufferGeometry();
  const dustSeeds = new Float32Array(DUST * 4);
  for (let i = 0; i < DUST; i++) {
    dustSeeds[i * 4] = rnd();
    dustSeeds[i * 4 + 1] = rnd();
    dustSeeds[i * 4 + 2] = rnd();
    dustSeeds[i * 4 + 3] = rnd();
  }
  dustGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(DUST * 3), 3));
  dustGeometry.setAttribute("aS", new THREE.BufferAttribute(dustSeeds, 4));
  const dustMaterial = new THREE.ShaderMaterial({
    uniforms: {
      ...shape, ...look, ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      uDust: { value: new THREE.Color() }, uReach: { value: 2 }, uPxScale: { value: 800 }, uPulse: { value: 0 },
      uHemiI: { value: 1 },
    },
    vertexShader: /* glsl */ `
      ${FUNNEL_SHAPE}
      attribute vec4 aS;
      uniform float uReach;
      uniform float uPxScale;
      uniform float uPulse;
      varying float vAlpha;
      varying float vSeed;
      #include <fog_pars_vertex>
      void main() {
        float life = fract(aS.y + uTime * (0.22 + 0.25 * aS.z));
        float ang = aS.w * 6.2831 + uTime * (1.4 + aS.z * 1.2) + life * 2.0;
        float r = uReach * (0.55 + aS.x * 0.95) * (0.75 + life * 0.7) * (1.0 + uPulse * 0.8);
        vec3 c = funnelAxis(life * life * 0.09);
        vec3 wp = vec3(c.x + cos(ang) * r, 0.25 + life * life * uReach * (0.6 + aS.z * 0.8), c.z + sin(ang) * r);
        vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        float size = uReach * (0.9 + aS.x * 1.3) * (0.6 + life * 0.8);
        gl_PointSize = uPxScale * size / max(-mvPosition.z, 0.1);
        vAlpha = sin(life * 3.14159) * (0.22 + 0.2 * aS.z);
        vSeed = aS.w;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */ `
      ${NOISE}
      uniform vec3 uDust;
      uniform vec3 uSunCol;
      uniform vec3 uSkyCol;
      uniform vec3 uGlowCol;
      uniform float uFlash;
      uniform float uHemiI;
      varying float vAlpha;
      varying float vSeed;
      #include <fog_pars_fragment>
      void main() {
        vec2 q = gl_PointCoord - 0.5;
        float d = length(q) * 2.0;
        if (d > 1.0) discard;
        float n = tt_noise(vec3(q * 5.0, vSeed * 40.0));
        float a = (1.0 - d * d) * (0.55 + 0.6 * n) * vAlpha;
        vec3 col = uDust * mix(uSkyCol, uSunCol, 0.5) * (0.45 + 0.25 * uHemiI) * (0.8 + 0.4 * n) + uGlowCol * uFlash * 0.2;
        gl_FragColor = vec4(col, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
    transparent: true,
    depthWrite: false,
    fog: true,
  });
  const dust = new THREE.Points(dustGeometry, dustMaterial);
  dust.frustumCulled = false;
  dust.renderOrder = 2;
  group.add(dust);

  const shells = [inner, outer, haze];
  const api = {
    group,
    shape,
    look,
    debris,
    reach: 2.3,
    applyTokens(t) {
      look.uColTop.value.copy(t.colors.funnelTop);
      look.uColBottom.value.copy(t.colors.funnelBottom);
      look.uGlowCol.value.copy(t.colors.funnelGlow);
      look.uCloudDark.value.copy(t.colors.cloudDark);
      look.uFunnelLight.value = t.numbers.funnelLight;
      const op = t.numbers.funnelOpacity || 0.92;
      for (const m of shells) m.material.uniforms.uOpacity.value = m.material.uniforms.uBaseOpacity.value * op;
      const d = chipMaterial.uniforms.uDebris.value;
      d[0].copy(t.colors.debrisA);
      d[1].copy(t.colors.debrisB);
      d[2].copy(t.colors.debrisC);
      dustMaterial.uniforms.uDust.value.copy(t.colors.dust);
    },
    setLighting({ sunDir, sunColor, sunI, skyColor, groundColor, hemiI }) {
      look.uSunDir.value.copy(sunDir);
      look.uSunCol.value.copy(sunColor);
      look.uSkyCol.value.copy(skyColor);
      look.uGroundCol.value.copy(groundColor);
      chipMaterial.uniforms.uSunI.value = sunI;
      chipMaterial.uniforms.uHemiI.value = hemiI;
      dustMaterial.uniforms.uHemiI.value = hemiI;
    },
    setChips(n) {
      chipGeometry.instanceCount = Math.min(n, MAX_CHIPS);
    },
    setPxScale(v) {
      dustMaterial.uniforms.uPxScale.value = v;
    },
    // pos: ground position; growth 0..1; lean: the top's lag behind the motion; pulse 0..1; flash 0..1
    update(time, pos, growth, lean, pulse, flash) {
      const size = funnelSize(growth);
      const flare = 1 + pulse * 0.18;
      shape.uTime.value = time;
      shape.uFunnelPos.value.set(pos.x, 0, pos.z);
      shape.uHeight.value = size.height;
      shape.uRBottom.value = size.rBottom * flare;
      shape.uRTop.value = size.rTop * (1 + pulse * 0.08);
      shape.uSway.value = 0.8 + growth * 1.2;
      shape.uLean.value.copy(lean);
      look.uFlash.value = flash;
      const beat = Math.max(0, Math.sin(time * 2.3) * Math.sin(time * 5.9 + 1.7));
      look.uFlick.value = look.uFunnelLight.value * (0.35 + 0.65 * Math.sqrt(beat));
      look.uSpinBoost.value = pulse * 1.6;
      dustMaterial.uniforms.uReach.value = size.reach;
      dustMaterial.uniforms.uPulse.value = pulse;
      api.reach = size.reach * (1 + pulse * 0.7);
    },
    // JavaScript mirror of FUNNEL_SHAPE, for props riding the spiral.
    axis(h, out) {
      const u = shape;
      const lean = h * h * u.uHeight.value * 0.35;
      const t = u.uTime.value;
      return out.set(
        u.uFunnelPos.value.x + u.uLean.value.x * lean + Math.sin(h * 3.1 + t * 0.8) * u.uSway.value * h,
        h * u.uHeight.value,
        u.uFunnelPos.value.z + u.uLean.value.y * lean + Math.cos(h * 2.3 + t * 0.63) * u.uSway.value * h,
      );
    },
    radius(h) {
      return shape.uRBottom.value + (shape.uRTop.value - shape.uRBottom.value) * Math.pow(h, 1.8);
    },
    height() {
      return shape.uHeight.value;
    },
  };
  api.applyTokens(tokens);
  return api;
}
