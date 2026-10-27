// The water itself: the back glass with its depth gradient and vignette, two god-ray planes falling from the surface,
// the bright underside of the surface, and the drifting motes that show the water has volume.
import * as THREE from "three";
import { shared, causticGLSL } from "./shading.js";
import { DEPTH_BACK } from "./world.js";

const colorspace = /* glsl */ `
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
`;

export function createWater(quality) {
  const group = new THREE.Group();
  const u = {
    uWater: { value: new THREE.Color() },
    uDeep: { value: new THREE.Color() },
    uKey: { value: new THREE.Color() },
    uLampColor: { value: new THREE.Color() },
    uLamp: { value: 0 },
    uDay: { value: 1 },
    uRays: { value: 1 },
    uRayColor: { value: new THREE.Color() },
  };

  const backMat = new THREE.ShaderMaterial({
    uniforms: { ...u, uCausticTime: shared.uCausticTime, uCaustic: shared.uCaustic },
    depthWrite: false,
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uWater, uDeep, uKey, uLampColor;
      uniform float uLamp, uDay, uCausticTime, uCaustic;
      varying vec2 vUv;
      ${causticGLSL}
      void main() {
        float g = smoothstep(0.0, 1.0, vUv.y);
        vec3 col = mix(uDeep, uWater, pow(clamp(g, 0.0, 1.0), 0.85));
        col += uWater * 0.45 * smoothstep(0.6, 1.0, vUv.y) * (0.3 + 0.7 * uDay);
        vec2 c = (vUv - 0.5) * vec2(1.25, 1.0);
        float vig = clamp(1.0 - dot(c, c) * 1.7, 0.0, 1.0);
        col *= mix(0.42, 1.0, vig);
        float sh = caustics(vec3(vUv.x * 9.0, 0.0, vUv.y * 5.0), uCausticTime * 0.7);
        col += uKey * sh * 0.04 * uCaustic * smoothstep(0.2, 0.9, vUv.y);
        float pool = exp(-pow((1.0 - vUv.y) * 2.6, 2.0)) * clamp(1.0 - abs(c.x) * 1.3, 0.0, 1.0);
        col += uLampColor * uLamp * 0.42 * pool;
        gl_FragColor = vec4(col, 1.0);
        ${colorspace}
      }
    `,
  });
  const back = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), backMat);
  back.renderOrder = -10;
  group.add(back);

  // god rays: tall trapezoids, narrow at the surface and wider at the floor, added to the light behind them
  const rayGeo = new THREE.PlaneGeometry(1, 1, 1, 8);
  {
    const p = rayGeo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const y = p.getY(i) + 0.5;
      p.setX(i, p.getX(i) * (1.9 - 0.9 * y));
    }
  }
  const rayMat = new THREE.ShaderMaterial({
    uniforms: { uRays: u.uRays, uRayColor: u.uRayColor, uTime: shared.uCausticTime, uSeed: { value: 0 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
    `,
    fragmentShader: /* glsl */ `
      uniform float uRays, uTime, uSeed;
      uniform vec3 uRayColor;
      varying vec2 vUv;
      void main() {
        float x = vUv.x, y = vUv.y;
        float s1 = sin(x * 13.0 + uTime * 0.31 + uSeed * 4.0);
        float s2 = sin(x * 29.0 - uTime * 0.23 + uSeed * 9.0);
        float s3 = sin(x * 7.0 + uTime * 0.17);
        float streaks = clamp(0.45 + 0.3 * s1 + 0.2 * s2 + 0.15 * s3, 0.0, 1.0);
        float edge = smoothstep(0.0, 0.3, x) * smoothstep(1.0, 0.7, x);
        float fall = pow(max(y, 0.0), 1.5) * smoothstep(0.0, 0.25, y);
        float a = edge * fall * streaks * uRays * 0.16;
        gl_FragColor = vec4(uRayColor * a, 1.0);
        ${colorspace}
      }
    `,
  });
  const rays = [0, 1].map((i) => {
    const m = new THREE.Mesh(rayGeo, rayMat.clone());
    m.material.uniforms.uSeed.value = i * 1.7;
    m.material.uniforms.uRays = u.uRays;
    m.material.uniforms.uRayColor = u.uRayColor;
    m.material.uniforms.uTime = shared.uCausticTime;
    m.renderOrder = 20;
    group.add(m);
    return m;
  });

  // the underside of the surface: bright, rippled, seen at a shallow angle across the top of the frame
  const surfMat = new THREE.ShaderMaterial({
    uniforms: { ...u, uCausticTime: shared.uCausticTime },
    side: THREE.DoubleSide,
    depthWrite: false,
    transparent: true,
    vertexShader: /* glsl */ `
      varying vec3 vW;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uWater, uKey, uLampColor;
      uniform float uDay, uLamp, uCausticTime;
      varying vec3 vW;
      ${causticGLSL}
      void main() {
        float c = caustics(vec3(vW.x * 0.6, 0.0, vW.z * 1.4), uCausticTime * 1.3);
        vec3 lit = mix(uWater * 1.25, uKey, 0.35 + 0.25 * uDay);
        vec3 col = (lit + uKey * c * (0.5 + 0.6 * uDay)) * (0.28 + 0.72 * uDay) + uLampColor * uLamp * (0.2 + 0.45 * c);
        gl_FragColor = vec4(col, 0.92);
        ${colorspace}
      }
    `,
  });
  const surface = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), surfMat);
  surface.rotation.x = Math.PI / 2;
  surface.renderOrder = -9;
  group.add(surface);

  // motes: tiny drifting specks, added light
  const count = quality.phone ? 110 : 240;
  const motes = new THREE.BufferGeometry();
  const mp = new Float32Array(count * 3);
  const ms = new Float32Array(count);
  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) {
    mp[i * 3] = rnd() * 2 - 1;
    mp[i * 3 + 1] = rnd();
    mp[i * 3 + 2] = rnd();
    ms[i] = rnd();
  }
  motes.setAttribute("position", new THREE.BufferAttribute(mp, 3));
  motes.setAttribute("aSeed", new THREE.BufferAttribute(ms, 1));
  const moteMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: shared.uTime, uBox: { value: new THREE.Vector4(8, 8, -3, 3) }, uColor: u.uRayColor, uDay: u.uDay,
      uScale: { value: 1 }, uLamp: u.uLamp,
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      uniform float uTime, uScale;
      uniform vec4 uBox;
      attribute float aSeed;
      varying float vA;
      void main() {
        float t = uTime * (0.02 + aSeed * 0.03);
        vec3 p = vec3(position.x * uBox.x, fract(position.y + t * 0.6) * uBox.y, mix(uBox.z, uBox.w, position.z));
        p.x += sin(uTime * 0.2 + aSeed * 30.0) * 0.3;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (1.2 + aSeed * 2.2) * uScale * (12.0 / -mv.z);
        vA = smoothstep(0.0, 0.08, fract(position.y + t * 0.6)) * smoothstep(1.0, 0.85, fract(position.y + t * 0.6));
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uDay, uLamp;
      varying float vA;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        float a = smoothstep(0.5, 0.0, d) * vA * (0.18 + 0.2 * uDay + 0.25 * uLamp);
        gl_FragColor = vec4(uColor * a, 1.0);
        ${colorspace}
      }
    `,
  });
  const moteMesh = new THREE.Points(motes, moteMat);
  moteMesh.frustumCulled = false;
  moteMesh.renderOrder = 22;
  group.add(moteMesh);

  function layout(frame, quality) {
    const r = frame.backRect;
    back.position.set((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, DEPTH_BACK - 1.6);
    back.scale.set((r.x1 - r.x0) * 1.15, (r.y1 - r.y0) * 1.15, 1);
    const sy = frame.surfaceY;
    surface.position.set(0, sy, (DEPTH_BACK - 1.6 + frame.base.z) / 2);
    surface.scale.set((r.x1 - r.x0) * 1.3, frame.base.z - DEPTH_BACK + 1.6, 1);
    const w = frame.tankW;
    const phone = frame.aspect < 0.8;
    rays[0].position.set(-w * (phone ? 0.12 : 0.18), sy * 0.52, -1.0);
    rays[0].scale.set(phone ? 2.4 : 3.6, sy * 1.15, 1);
    rays[0].rotation.z = -0.2;
    rays[1].position.set(w * (phone ? 0.2 : 0.22), sy * 0.5, -2.2);
    rays[1].scale.set(phone ? 1.8 : 2.8, sy * 1.15, 1);
    rays[1].rotation.z = -0.14;
    rays[0].userData.d = 0;
    rays[1].userData.d = 0;
    moteMat.uniforms.uBox.value.set(w * 0.5, sy, DEPTH_BACK + 0.2, 2.4);
    moteMat.uniforms.uScale.value = quality.dpr * (phone ? 1.4 : 1);
  }

  function update(mood, pal, t, motion) {
    u.uWater.value.copy(mood.water);
    u.uDeep.value.copy(mood.deep);
    u.uKey.value.copy(mood.key);
    u.uLampColor.value.copy(pal.lamp);
    u.uLamp.value = mood.lamp;
    u.uDay.value = mood.day;
    u.uRays.value = mood.rays;
    u.uRayColor.value.copy(pal.ray).lerp(mood.key, 0.5);
    const drift = motion ? Math.sin(t * 0.05) * 0.35 : 0;
    rays[0].position.x += (drift - (rays[0].userData.d || 0));
    rays[0].userData.d = drift;
    rays[1].position.x -= (drift * 0.7 - (rays[1].userData.d || 0));
    rays[1].userData.d = drift * 0.7;
  }

  return { group, layout, update };
}
