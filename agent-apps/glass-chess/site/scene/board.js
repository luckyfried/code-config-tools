// The board: a lacquered slab, a painted top (squares, inlay, coordinates), a mirror plane at the theme's strength
// with a ripple a capture can start, the red check square the glass refracts, the move hints, and the soft shadows
// under each piece.
import * as THREE from "three";
import { Reflector } from "three/addons/objects/Reflector.js";

export const SIZE = 9.4;
export const FILES = "abcdefgh";
export const squareXZ = (sq) => [FILES.indexOf(sq[0]) - 3.5, 3.5 - (Number(sq[1]) - 1)];
export const xzSquare = (x, z) => {
  const f = Math.floor(x + 4), r = Math.floor(4 - z);
  return f >= 0 && f < 8 && r >= 0 && r < 8 ? FILES[f] + (r + 1) : null;
};

const ONLY_MAIN = 1; // a layer the mirror's camera never draws

function roundedRect(w, h, r) {
  const s = new THREE.Shape();
  s.moveTo(-w / 2 + r, -h / 2);
  s.lineTo(w / 2 - r, -h / 2);
  s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
  s.lineTo(w / 2, h / 2 - r);
  s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2);
  s.lineTo(-w / 2 + r, h / 2);
  s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
  s.lineTo(-w / 2, -h / 2 + r);
  s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  return s;
}

// A seeded random so the grain and the veins are the same on every load.
function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function paintTop(tokens, px) {
  const c = document.createElement("canvas");
  c.width = c.height = px;
  const g = c.getContext("2d");
  const unit = px / SIZE;
  const field = unit * 8;
  const o = (px - field) / 2;
  const style = tokens.css("--board-style");
  const rand = rng(7);

  g.fillStyle = tokens.css("--board-frame");
  g.fillRect(0, 0, px, px);
  if (style === "wood") {
    for (let i = 0; i < 260; i++) {
      g.strokeStyle = tokens.css("--board-frame-grain");
      g.globalAlpha = 0.05 + rand() * 0.12;
      g.lineWidth = 1 + rand() * 3;
      const y = rand() * px;
      g.beginPath();
      g.moveTo(0, y);
      g.bezierCurveTo(px * 0.3, y + rand() * 18 - 9, px * 0.6, y + rand() * 18 - 9, px, y + rand() * 10 - 5);
      g.stroke();
    }
    g.globalAlpha = 1;
  }

  const light = tokens.css("--board-light"), dark = tokens.css("--board-dark");
  for (let f = 0; f < 8; f++) {
    for (let r = 0; r < 8; r++) {
      const isLight = (f + r) % 2 === 0;
      const x = o + f * unit, y = o + r * unit;
      g.fillStyle = isLight ? light : dark;
      g.fillRect(x, y, unit + 0.5, unit + 0.5);
      g.save();
      g.beginPath();
      g.rect(x, y, unit, unit);
      g.clip();
      if (style === "wood") {
        g.strokeStyle = tokens.css(isLight ? "--board-light-grain" : "--board-dark-grain");
        const vertical = (f + r) % 2 === 0;
        for (let i = 0; i < 34; i++) {
          g.globalAlpha = 0.1 + rand() * 0.2;
          g.lineWidth = 0.8 + rand() * 2.4;
          g.beginPath();
          const t = rand() * unit;
          if (vertical) { g.moveTo(x + t, y); g.bezierCurveTo(x + t + 6, y + unit * 0.3, x + t - 6, y + unit * 0.7, x + t + rand() * 4, y + unit); }
          else { g.moveTo(x, y + t); g.bezierCurveTo(x + unit * 0.3, y + t + 6, x + unit * 0.7, y + t - 6, x + unit, y + t + rand() * 4); }
          g.stroke();
        }
      } else if (style === "marble") {
        g.strokeStyle = tokens.css(isLight ? "--board-light-vein" : "--board-dark-vein");
        for (let i = 0; i < 7; i++) {
          g.globalAlpha = 0.12 + rand() * 0.3;
          g.lineWidth = 0.6 + rand() * 2.2;
          let vx = x + rand() * unit, vy = y;
          g.beginPath();
          g.moveTo(vx, vy);
          while (vy < y + unit) { vx += (rand() - 0.5) * 14; vy += 8 + rand() * 8; g.lineTo(vx, vy); }
          g.stroke();
        }
      } else {
        // Lacquer: a soft depth gradient across each square.
        const grad = g.createLinearGradient(x, y, x + unit, y + unit);
        grad.addColorStop(0, "rgba(255,255,255,0.05)");
        grad.addColorStop(1, "rgba(0,0,0,0.08)");
        g.fillStyle = grad;
        g.globalAlpha = 1;
        g.fillRect(x, y, unit, unit);
      }
      g.restore();
      g.globalAlpha = 1;
    }
  }

  // The inlay around the field and a hairline between the squares.
  g.strokeStyle = tokens.css("--board-inlay");
  g.lineWidth = unit * 0.035;
  g.strokeRect(o - unit * 0.09, o - unit * 0.09, field + unit * 0.18, field + unit * 0.18);
  g.lineWidth = unit * 0.012;
  g.strokeRect(o - unit * 0.16, o - unit * 0.16, field + unit * 0.32, field + unit * 0.32);
  g.globalAlpha = 0.35;
  g.lineWidth = Math.max(1, unit * 0.006);
  g.strokeRect(o, o, field, field);
  g.globalAlpha = 1;

  // Coordinates, upright for each player.
  g.fillStyle = tokens.css("--board-coords");
  g.font = `600 ${Math.round(unit * 0.24)}px ${tokens.css("--font-sans")}`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  const edge = o - unit * 0.42;
  for (let i = 0; i < 8; i++) {
    const cx = o + (i + 0.5) * unit;
    g.fillText(FILES[i], cx, px - edge);
    g.fillText(String(8 - i), edge, cx);
    g.save();
    g.translate(cx, edge);
    g.rotate(Math.PI);
    g.fillText(FILES[i], 0, 0);
    g.restore();
    g.save();
    g.translate(px - edge, cx);
    g.rotate(Math.PI);
    g.fillText(String(8 - i), 0, 0);
    g.restore();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

const MIRROR_SHADER = {
  name: "BoardMirror",
  uniforms: {
    color: { value: null },
    tDiffuse: { value: null },
    textureMatrix: { value: null },
    uStrength: { value: 0.25 },
    uTime: { value: 0 },
    uRipples: { value: [new THREE.Vector4(0, 0, -99, 0), new THREE.Vector4(0, 0, -99, 0)] },
    uRippleColor: { value: new THREE.Color(1, 1, 1) },
  },
  vertexShader: /* glsl */`
    uniform mat4 textureMatrix;
    varying vec4 vUv;
    varying vec3 vWorld;
    #include <common>
    #include <logdepthbuf_pars_vertex>
    void main() {
      vUv = textureMatrix * vec4(position, 1.0);
      vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      #include <logdepthbuf_vertex>
    }`,
  fragmentShader: /* glsl */`
    uniform vec3 color;
    uniform sampler2D tDiffuse;
    uniform float uStrength;
    uniform float uTime;
    uniform vec4 uRipples[2];
    uniform vec3 uRippleColor;
    varying vec4 vUv;
    varying vec3 vWorld;
    #include <logdepthbuf_pars_fragment>
    void main() {
      #include <logdepthbuf_fragment>
      vec4 uv = vUv;
      float glow = 0.0;
      for (int i = 0; i < 2; i++) {
        vec4 rp = uRipples[i];
        float age = uTime - rp.z;
        if (age < 0.0 || age > 1.6) continue;
        vec2 d = vWorld.xz - rp.xy;
        float dist = length(d);
        float front = age * 2.6;
        float band = exp(-pow((dist - front) * 3.2, 2.0));
        float fade = (1.0 - age / 1.6) * rp.w;
        float wave = sin((dist - front) * 22.0) * band * fade;
        uv.xy += normalize(d + 1e-4) * wave * 0.035 * uv.w;
        glow += band * fade * (0.5 + 0.5 * wave);
      }
      vec4 base = texture2DProj(tDiffuse, uv);
      vec3 rgb = base.rgb * color + uRippleColor * glow * 0.35;
      gl_FragColor = vec4(rgb, clamp(uStrength * base.a + glow * 0.3, 0.0, 1.0));
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
};

const HINT_VERTEX = /* glsl */`
  attribute vec4 aColor;
  attribute float aKind;
  varying vec4 vColor;
  varying float vKind;
  varying vec2 vUv;
  void main() {
    vColor = aColor;
    vKind = aKind;
    vUv = uv * 2.0 - 1.0;
    gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
  }`;
const HINT_FRAGMENT = /* glsl */`
  uniform float uTime;
  varying vec4 vColor;
  varying float vKind;
  varying vec2 vUv;
  void main() {
    float r = length(vUv);
    float a = 0.0;
    if (vKind < 0.5) {
      vec2 q = abs(vUv);
      float edge = max(q.x, q.y);
      a = 0.55 + 0.45 * smoothstep(0.78, 0.98, edge);
    } else if (vKind < 1.5) {
      a = 1.0 - smoothstep(0.24, 0.3, r);
      a += 0.35 * (1.0 - smoothstep(0.3, 0.52, r));
    } else if (vKind < 2.5) {
      a = smoothstep(0.7, 0.76, r) * (1.0 - smoothstep(0.9, 0.96, r));
    } else {
      vec2 q = abs(vUv);
      float edge = max(q.x, q.y);
      a = smoothstep(0.84, 0.88, edge) * (1.0 - smoothstep(0.97, 1.0, edge));
      a *= 0.75 + 0.25 * sin(uTime * 5.0);
    }
    if (a < 0.01) discard;
    gl_FragColor = vec4(vColor.rgb, vColor.a * a);
    #include <colorspace_fragment>
  }`;

const SHADOW_VERTEX = /* glsl */`
  attribute float aOpacity;
  varying float vOpacity;
  varying vec2 vUv;
  void main() {
    vOpacity = aOpacity;
    vUv = uv * 2.0 - 1.0;
    gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
  }`;
const SHADOW_FRAGMENT = /* glsl */`
  uniform vec3 uColor;
  varying float vOpacity;
  varying vec2 vUv;
  void main() {
    float r = length(vUv);
    float body = exp(-r * r * 4.0);
    float lens = exp(-r * r * 22.0);
    float a = vOpacity * max(0.0, body - 0.55 * lens);
    if (a < 0.003) discard;
    gl_FragColor = vec4(uColor, a);
    #include <colorspace_fragment>
  }`;

export class Board {
  constructor({ tokens, tier, renderer }) {
    this.group = new THREE.Group();
    this.tokens = tokens;
    this.ripple = 0;

    const slabShape = roundedRect(SIZE, SIZE, 0.32);
    const slab = new THREE.Mesh(
      new THREE.ExtrudeGeometry(slabShape, { depth: 0.36, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.06, bevelSegments: 4, curveSegments: 8 }),
      new THREE.MeshPhysicalMaterial({ color: tokens.color("--board-frame"), roughness: 0.38, clearcoat: 1, clearcoatRoughness: 0.08 }),
    );
    slab.rotation.x = -Math.PI / 2;
    slab.position.y = -0.42;
    this.slab = slab;
    this.group.add(slab);

    this.topMaterial = new THREE.MeshPhysicalMaterial({
      map: paintTop(tokens, tier === "desktop" ? 4096 : 2048),
      roughness: tokens.number("--board-roughness", 0.4),
      clearcoat: 1,
      clearcoatRoughness: tokens.number("--board-clearcoat-roughness", 0.06),
    });
    const top = new THREE.Mesh(new THREE.PlaneGeometry(SIZE - 0.02, SIZE - 0.02), this.topMaterial);
    top.rotation.x = -Math.PI / 2;
    top.position.y = 0.001;
    this.top = top;
    this.group.add(top);

    // The soft pool of shade the slab throws on the table.
    const pool = new THREE.Mesh(
      new THREE.PlaneGeometry(SIZE * 1.9, SIZE * 1.9),
      new THREE.ShaderMaterial({
        transparent: true, depthWrite: false,
        uniforms: { uColor: { value: tokens.color("--table-shadow") }, uOpacity: { value: tokens.number("--table-shadow-opacity", 0.5) } },
        vertexShader: "varying vec2 vUv; void main(){ vUv = uv*2.0-1.0; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uOpacity;
          varying vec2 vUv;
          void main() {
            vec2 q = max(abs(vUv) - 0.38, 0.0);
            float d = length(q) / 0.62;
            gl_FragColor = vec4(uColor, uOpacity * exp(-d * d * 6.0));
            #include <colorspace_fragment>
          }`,
      }),
    );
    pool.rotation.x = -Math.PI / 2;
    pool.position.y = -0.55;
    pool.layers.set(ONLY_MAIN);
    this.group.add(pool);

    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const mirrorScale = tier === "desktop" ? 0.6 : 0.4;
    this.mirror = new Reflector(new THREE.PlaneGeometry(SIZE - 0.02, SIZE - 0.02), {
      shader: MIRROR_SHADER,
      textureWidth: Math.round(window.innerWidth * ratio * mirrorScale),
      textureHeight: Math.round(window.innerHeight * ratio * mirrorScale),
      color: tokens.color("--mirror-tint"),
      multisample: 0,
    });
    this.mirror.material.transparent = true;
    this.mirror.material.depthWrite = false;
    this.mirror.material.uniforms.uStrength.value = tokens.number("--mirror-strength", 0.25);
    this.mirror.material.uniforms.uRippleColor.value = tokens.color("--ripple");
    this.mirror.rotation.x = -Math.PI / 2;
    this.mirror.position.y = 0.006;
    this.mirror.renderOrder = 1;
    this.group.add(this.mirror);

    // The check square: opaque, so the glass king refracts its red.
    this.checkMaterial = new THREE.MeshBasicMaterial({ color: tokens.color("--check"), toneMapped: false });
    this.checkSquare = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), this.checkMaterial);
    this.checkSquare.rotation.x = -Math.PI / 2;
    this.checkSquare.position.y = -2;
    this.group.add(this.checkSquare);
    this.checkBase = new THREE.Color();
    this.checkRed = tokens.color("--check");

    // Hints: selected square, last move, legal targets, the keyboard cursor.
    this.hintMax = 40;
    const hintGeo = new THREE.PlaneGeometry(1, 1);
    hintGeo.setAttribute("aColor", new THREE.InstancedBufferAttribute(new Float32Array(this.hintMax * 4), 4));
    hintGeo.setAttribute("aKind", new THREE.InstancedBufferAttribute(new Float32Array(this.hintMax), 1));
    this.hintTime = { value: 0 };
    this.hints = new THREE.InstancedMesh(hintGeo, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, uniforms: { uTime: this.hintTime },
      vertexShader: HINT_VERTEX, fragmentShader: HINT_FRAGMENT,
    }), this.hintMax);
    this.hints.count = 0;
    this.hints.renderOrder = 2;
    this.hints.frustumCulled = false;
    this.hints.layers.set(ONLY_MAIN);
    this.group.add(this.hints);

    // One soft shadow per piece, lighter at the center where the glass gathers light.
    this.shadowMax = 40;
    const shadowGeo = new THREE.PlaneGeometry(1, 1);
    shadowGeo.setAttribute("aOpacity", new THREE.InstancedBufferAttribute(new Float32Array(this.shadowMax), 1));
    this.shadows = new THREE.InstancedMesh(shadowGeo, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false,
      uniforms: { uColor: { value: tokens.color("--piece-shadow") } },
      vertexShader: SHADOW_VERTEX, fragmentShader: SHADOW_FRAGMENT,
    }), this.shadowMax);
    this.shadows.count = 0;
    this.shadows.renderOrder = 1;
    this.shadows.frustumCulled = false;
    this.shadows.layers.set(ONLY_MAIN);
    this.group.add(this.shadows);
    this.tmp = new THREE.Object3D();
    this.shadowStrength = tokens.number("--piece-shadow-opacity", 0.6);
  }

  setHints(list) {
    const color = this.hints.geometry.attributes.aColor, kind = this.hints.geometry.attributes.aKind;
    const n = Math.min(list.length, this.hintMax);
    for (let i = 0; i < n; i++) {
      const h = list[i];
      const [x, z] = squareXZ(h.square);
      this.tmp.position.set(x, 0.008 + i * 0.0001, z);
      this.tmp.rotation.set(-Math.PI / 2, 0, 0);
      this.tmp.scale.setScalar(h.kind === "dot" ? 0.9 : 1);
      this.tmp.updateMatrix();
      this.hints.setMatrixAt(i, this.tmp.matrix);
      const c = h.color;
      color.setXYZW(i, c.r, c.g, c.b, h.alpha ?? 1);
      kind.setX(i, { fill: 0, dot: 1, ring: 2, cursor: 3 }[h.kind]);
    }
    this.hints.count = n;
    this.hints.instanceMatrix.needsUpdate = true;
    color.needsUpdate = true;
    kind.needsUpdate = true;
  }

  // Shadows: [{ x, z, lift, radius }]; a lifted piece throws a wider, fainter shadow.
  setShadows(list) {
    const op = this.shadows.geometry.attributes.aOpacity;
    const n = Math.min(list.length, this.shadowMax);
    for (let i = 0; i < n; i++) {
      const s = list[i];
      const spread = 1 + s.lift * 0.9;
      this.tmp.position.set(s.x + s.lift * 0.18, 0.007, s.z + s.lift * 0.12);
      this.tmp.rotation.set(-Math.PI / 2, 0, 0);
      this.tmp.scale.setScalar(s.radius * 3.4 * spread);
      this.tmp.updateMatrix();
      this.shadows.setMatrixAt(i, this.tmp.matrix);
      op.setX(i, (this.shadowStrength * s.alpha) / (spread * spread));
    }
    this.shadows.count = n;
    this.shadows.instanceMatrix.needsUpdate = true;
    op.needsUpdate = true;
  }

  rippleAt(square, now, strength = 1) {
    const [x, z] = squareXZ(square);
    const slot = this.mirror.material.uniforms.uRipples.value[this.ripple++ % 2];
    slot.set(x, z, now, strength);
  }

  setCheck(square, pulse) {
    // With no check the square waits under the slab, so its shader is ready before the first check.
    if (!square) { this.checkSquare.position.y = -2; return; }
    const [x, z] = squareXZ(square);
    this.checkSquare.position.set(x, 0.003, z);
    const isLight = (FILES.indexOf(square[0]) + Number(square[1])) % 2 === 1;
    this.checkBase.set(this.tokens.css(isLight ? "--board-light" : "--board-dark"));
    this.checkMaterial.color.copy(this.checkBase).lerp(this.checkRed, 0.45 + 0.55 * pulse);
  }

  tick(now) {
    this.mirror.material.uniforms.uTime.value = now;
    this.hintTime.value = now;
  }
}

export { ONLY_MAIN };
