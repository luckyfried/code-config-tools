// Neon signs: one atlas painted on a canvas, every sign one instance of one plane, tinted by the theme's sign colors.
import * as THREE from "three";
import { FOG_GLSL } from "./palette.js";

const SIZE = 2048;

function fitFont(ctx, text, maxW, maxH, weight) {
  let size = maxH;
  ctx.font = `${weight} ${size}px "Big Shoulders", "Arial Narrow", sans-serif`;
  const w = ctx.measureText(text).width;
  if (w > maxW) size = Math.floor((size * maxW) / w);
  ctx.font = `${weight} ${size}px "Big Shoulders", "Arial Narrow", sans-serif`;
  return size;
}

// Red is the lit tube, green the glow around it, blue the dark backing plate.
function paintSlot(ctx, text, x, y, w, h, vertical) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.fillStyle = "rgb(0,0,255)";
  const pad = Math.round(Math.min(w, h) * 0.08);
  ctx.fillRect(x + pad * 0.5, y + pad * 0.5, w - pad, h - pad);
  const drawText = (color, blur) => {
    ctx.shadowColor = color;
    ctx.shadowBlur = blur;
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, Math.min(w, h) * 0.018);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    if (vertical) {
      const letters = [...text];
      const step = (h - pad * 3) / letters.length;
      const size = fitFont(ctx, "W", w - pad * 3, step * 0.98, 800);
      letters.forEach((ch, i) => ctx.fillText(ch, x + w / 2, y + pad * 1.5 + step * (i + 0.5) + size * 0.04));
    } else {
      fitFont(ctx, text, w - pad * 4, (h - pad * 3) * 0.92, 800);
      ctx.fillText(text, x + w / 2, y + h / 2 + h * 0.03);
    }
    ctx.strokeRect(x + pad * 1.1, y + pad * 1.1, w - pad * 2.2, h - pad * 2.2);
  };
  ctx.globalCompositeOperation = "lighter";
  drawText("rgb(0,255,0)", Math.min(w, h) * 0.12);
  ctx.shadowBlur = 0;
  drawText("rgb(255,0,0)", 0);
  ctx.restore();
}

export function paintSignAtlas(words, verticalWords, cityName) {
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, SIZE, SIZE);
  const rects = new Map();
  const slot = (key, x, y, w, h, vertical, text) => {
    paintSlot(ctx, text, x, y, w, h, vertical);
    rects.set(key, [x / SIZE, 1 - (y + h) / SIZE, w / SIZE, h / SIZE]);
  };
  slot(`name`, 0, 0, SIZE, 420, false, cityName.toUpperCase());
  words.forEach((word, i) => slot(`h:${word}`, (i % 4) * 512, 440 + Math.floor(i / 4) * 128, 512, 124, false, word));
  verticalWords.forEach((word, i) => slot(`v:${word}`, i * 128, 1100, 124, 720, true, word));
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.NoColorSpace;
  texture.anisotropy = 8;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  return { texture, rects };
}

export function buildSigns(plan, atlas, shared) {
  const signs = plan.signs;
  const geometry = new THREE.InstancedBufferGeometry();
  const plane = new THREE.PlaneGeometry(1, 1);
  geometry.index = plane.index;
  geometry.setAttribute("position", plane.getAttribute("position"));
  geometry.setAttribute("uv", plane.getAttribute("uv"));
  const offset = new Float32Array(signs.length * 3);
  const size = new Float32Array(signs.length * 3);
  const rect = new Float32Array(signs.length * 4);
  const look = new Float32Array(signs.length * 3);
  signs.forEach((s, i) => {
    offset.set([s.x, s.y, s.z], i * 3);
    size.set([s.w, s.h, Math.atan2(s.nx, s.nz)], i * 3);
    const key = s.big ? "name" : `${s.vertical ? "v" : "h"}:${s.text}`;
    const r = atlas.rects.get(key) || atlas.rects.get("name");
    rect.set(r, i * 4);
    look.set([s.color, s.flicker, s.big ? 1 : 0], i * 3);
  });
  geometry.setAttribute("aOffset", new THREE.InstancedBufferAttribute(offset, 3));
  geometry.setAttribute("aSize", new THREE.InstancedBufferAttribute(size, 3));
  geometry.setAttribute("aRect", new THREE.InstancedBufferAttribute(rect, 4));
  geometry.setAttribute("aLook", new THREE.InstancedBufferAttribute(look, 3));
  geometry.instanceCount = signs.length;

  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...shared,
      uAtlas: { value: atlas.texture },
      uSign1: { value: new THREE.Color() },
      uSign2: { value: new THREE.Color() },
      uSign3: { value: new THREE.Color() },
      uPlate: { value: new THREE.Color() },
    },
    vertexShader: /* glsl */ `
      attribute vec3 aOffset;
      attribute vec3 aSize;
      attribute vec4 aRect;
      attribute vec3 aLook;
      varying vec2 vUv;
      varying vec3 vWorld;
      varying vec3 vLook;
      void main() {
        float c = cos(aSize.z), s = sin(aSize.z);
        vec3 p = vec3(position.x * aSize.x, position.y * aSize.y, 0.0);
        vec3 world = aOffset + vec3(p.x * c, p.y, -p.x * s);
        vUv = aRect.xy + uv * aRect.zw;
        vWorld = world;
        vLook = aLook;
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uAtlas;
      uniform vec3 uSign1;
      uniform vec3 uSign2;
      uniform vec3 uSign3;
      uniform vec3 uPlate;
      uniform float uTime;
      uniform float uGlow;
      varying vec2 vUv;
      varying vec3 vWorld;
      varying vec3 vLook;
      ${FOG_GLSL}
      float hash(float n) { return fract(sin(n) * 43758.5453); }
      void main() {
        vec3 t = texture2D(uAtlas, vUv).rgb;
        vec3 tint = vLook.x < 0.5 ? uSign1 : vLook.x < 1.5 ? uSign2 : uSign3;
        float on = 1.0;
        if (vLook.y >= 0.0) {
          float k = floor(uTime * 9.0 + vLook.y * 40.0);
          on = mix(0.15, 1.0, step(0.22, hash(k)));
        }
        float big = vLook.z;
        float intensity = (2.2 + big * 1.4) * on * mix(0.75, 1.0, uGlow);
        vec3 core = mix(tint, vec3(1.0), 0.35) * t.r * intensity;
        vec3 glow = tint * t.g * 0.9 * on;
        float dist = length(vWorld - cameraPosition);
        // Signs burn through the rain a little longer than the walls do.
        float keep = 0.35 * (1.0 - smoothstep(120.0, 380.0, dist));
        float fog = fogAmount(vWorld, cameraPosition) * (1.0 - keep);
        // The backing plate covers what is behind it; the tube and its glow add light on top, so the glow brightens
        // a dusk sky as well as a night one instead of tinting it toward the plate.
        float cover = max(t.b * 0.92, t.r);
        vec3 plate = mix(uPlate, applyFog(uPlate, vWorld, cameraPosition), 1.0 - keep) * t.b * 0.92;
        vec3 light = (core + glow) * (1.0 - fog * 0.85);
        if (cover < 0.02 && max(light.r, max(light.g, light.b)) < 0.004) discard;
        gl_FragColor = vec4(plate + light, cover);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    blending: THREE.CustomBlending,
    blendSrc: THREE.OneFactor,
    blendDst: THREE.OneMinusSrcAlphaFactor,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.renderOrder = 2;
  mesh.name = "signs";
  const halo = buildHalos(geometry, shared);
  mesh.add(halo);
  mesh.userData.halo = halo;
  return mesh;
}

// The light a lit sign throws on the wall and the wet air around it: one larger plane per sign, drawn before the
// signs and added to what is behind, so every sign has a halo on every tier, bloom or not.
function buildHalos(geometry, shared) {
  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...shared,
      uSign1: { value: new THREE.Color() },
      uSign2: { value: new THREE.Color() },
      uSign3: { value: new THREE.Color() },
      uHalo: { value: 0 },
    },
    vertexShader: /* glsl */ `
      attribute vec3 aOffset;
      attribute vec3 aSize;
      attribute vec3 aLook;
      varying vec2 vLocal;
      varying vec2 vHalf;
      varying float vMargin;
      varying vec3 vWorld;
      varying vec3 vLook;
      void main() {
        float margin = min(aSize.x, aSize.y) * 0.9 + 0.8;
        vec2 full = aSize.xy + 2.0 * margin;
        vec2 local = position.xy * full;
        float c = cos(aSize.z), s = sin(aSize.z);
        vec3 world = aOffset + vec3(local.x * c, local.y, -local.x * s);
        vLocal = local;
        vHalf = aSize.xy * 0.5;
        vMargin = margin;
        vWorld = world;
        vLook = aLook;
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uSign1;
      uniform vec3 uSign2;
      uniform vec3 uSign3;
      uniform float uHalo;
      uniform float uTime;
      varying vec2 vLocal;
      varying vec2 vHalf;
      varying float vMargin;
      varying vec3 vWorld;
      varying vec3 vLook;
      ${FOG_GLSL}
      float hash(float n) { return fract(sin(n) * 43758.5453); }
      void main() {
        vec3 tint = vLook.x < 0.5 ? uSign1 : vLook.x < 1.5 ? uSign2 : uSign3;
        float on = 1.0;
        if (vLook.y >= 0.0) {
          float k = floor(uTime * 9.0 + vLook.y * 40.0);
          on = mix(0.15, 1.0, step(0.22, hash(k)));
        }
        vec2 q = abs(vLocal) - vHalf;
        float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
        float fall = 1.0 - clamp(d / vMargin, 0.0, 1.0);
        fall = fall * fall * (0.35 + 0.65 * fall);
        float dist = length(vWorld - cameraPosition);
        float keep = 0.35 * (1.0 - smoothstep(120.0, 380.0, dist));
        float fog = fogAmount(vWorld, cameraPosition) * (1.0 - keep);
        vec3 color = tint * fall * on * uHalo * (1.0 + vLook.z * 0.5) * (1.0 - fog * 0.85);
        if (max(color.r, max(color.g, color.b)) < 0.003) discard;
        gl_FragColor = vec4(color, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const halo = new THREE.Mesh(geometry, material);
  halo.frustumCulled = false;
  halo.renderOrder = 1;
  halo.name = "sign halos";
  return halo;
}

export function updateSignPalette(mesh, palette) {
  const u = mesh.material.uniforms;
  u.uSign1.value.copy(palette.sign1);
  u.uSign2.value.copy(palette.sign2);
  u.uSign3.value.copy(palette.sign3);
  u.uPlate.value.copy(palette.roof).multiplyScalar(0.8);
  const h = mesh.userData.halo.material.uniforms;
  h.uSign1.value.copy(palette.sign1);
  h.uSign2.value.copy(palette.sign2);
  h.uSign3.value.copy(palette.sign3);
  h.uHalo.value = palette.signHalo;
}
