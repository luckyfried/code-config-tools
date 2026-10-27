// The wind layer: one draw of point sprites a frame. Every particle's place is a formula of its seed, the time, the
// wind, and the scroll, worked out on the graphics card, so the page keeps no particle state between frames.
import petals from "./particles/petals.js";
import embers from "./particles/embers.js";
import confetti from "./particles/confetti.js";
import lanterns from "./particles/lanterns.js";

const KINDS = { wedding: petals, party: embers, birthday: confetti, reunion: lanterns };

const VERTEX = `
attribute vec4 aSeed;
attribute vec2 aMore;
uniform vec2 uView;
uniform float uTime;
uniform float uWind;
uniform float uScroll;
uniform float uDensity;
uniform float uDpr;
uniform vec2 uSize;
uniform vec2 uFall;
uniform vec2 uSway;
uniform vec2 uAlpha;
uniform float uSpin;
uniform float uFlip;
uniform vec3 uC1;
uniform vec3 uC2;
uniform vec3 uC3;
varying vec3 vColor;
varying float vAlpha;
varying float vRot;
varying float vFlip;
varying float vSeed;

void main() {
  float depth = aSeed.z;
  float margin = 40.0;
  vec2 span = uView + 2.0 * margin;
  float speed = mix(uFall.x, uFall.y, aSeed.y) * (0.55 + 0.45 * depth);
  float phase = aMore.x * 6.2831;
  float y = aSeed.w * span.y + uTime * speed - uScroll * (0.08 + 0.32 * depth);
  y = mod(y, span.y) - margin;
  float sway = mix(uSway.x, uSway.y, aMore.y) * sin(uTime * (0.35 + aSeed.y * 0.6) + phase);
  float x = aSeed.x * span.x + uWind * (0.45 + 0.75 * depth) + sway;
  x = mod(x, span.x) - margin;
  vec2 clip = vec2(x / uView.x * 2.0 - 1.0, 1.0 - y / uView.y * 2.0);
  gl_Position = vec4(clip, 0.0, 1.0);
  float visible = step(aMore.y, uDensity);
  gl_PointSize = mix(uSize.x, uSize.y, depth * depth) * uDpr * visible;
  float pick = fract(aSeed.x * 7.13 + aSeed.y * 3.71);
  vColor = pick < 0.45 ? uC1 : (pick < 0.8 ? uC2 : uC3);
  float twinkle = uSpin == 0.0 ? 0.65 + 0.35 * sin(uTime * (1.2 + aSeed.y * 2.4) + phase) : 1.0;
  vAlpha = mix(uAlpha.x, uAlpha.y, depth) * twinkle;
  vRot = phase + uTime * uSpin * (aSeed.y - 0.5) * 2.0;
  vFlip = uFlip == 0.0 ? 1.0 : sin(uTime * uFlip * (0.4 + aMore.x) + phase);
  vSeed = aMore.x;
}
`;

const FRAGMENT = `
precision mediump float;
uniform float uShape;
varying vec3 vColor;
varying float vAlpha;
varying float vRot;
varying float vFlip;
varying float vSeed;

void main() {
  vec2 p = gl_PointCoord * 2.0 - 1.0;
  float c = cos(vRot);
  float s = sin(vRot);
  p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
  float a = 0.0;
  vec3 color = vColor;
  if (uShape < 0.5) {
    float f = max(abs(vFlip), 0.34);
    vec2 q = vec2(p.x / (0.62 * f), p.y);
    q.y += 0.25 * q.x * q.x;
    float d = length(vec2(q.x, q.y * (q.y < 0.0 ? 1.05 : 1.35)));
    a = 1.0 - smoothstep(0.78, 0.96, d);
    color = mix(color, vec3(1.0), 0.28 * (1.0 - smoothstep(0.0, 0.8, d)) * step(0.0, vFlip));
    color *= 0.86 + 0.14 * f;
  } else if (uShape < 1.5) {
    float r = dot(p, p);
    a = exp(-r * 5.0) + 0.6 * (1.0 - smoothstep(0.02, 0.09, r));
    color = mix(color, vec3(1.0, 0.95, 0.8), 1.0 - smoothstep(0.0, 0.12, r));
  } else if (uShape < 2.5) {
    float f = max(abs(vFlip), 0.12);
    vec2 q = abs(vec2(p.x / f, p.y));
    float w = vSeed > 0.5 ? 0.42 : 0.62;
    a = (1.0 - smoothstep(w - 0.1, w, q.x)) * (1.0 - smoothstep(0.86, 0.96, q.y));
    color *= 0.78 + 0.22 * f;
  } else {
    float r = length(p);
    a = (1.0 - smoothstep(0.12, 0.3, r)) * 0.95 + exp(-r * r * 7.0) * 0.55;
    color = mix(color, vec3(1.0, 0.97, 0.88), 1.0 - smoothstep(0.0, 0.22, r));
  }
  a *= vAlpha;
  if (a < 0.01) discard;
  gl_FragColor = vec4(color * a, a);
}
`;

function hexColor(value) {
  const v = value.trim();
  let m = /^#([0-9a-f]{3})$/i.exec(v);
  if (m) return [...m[1]].map((h) => parseInt(h + h, 16) / 255);
  m = /^#([0-9a-f]{6})/i.exec(v);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
  m = /rgba?\(([^)]+)\)/i.exec(v);
  if (m) return m[1].split(/[\s,/]+/).slice(0, 3).map((n) => Number(n) / 255);
  return [1, 1, 1];
}

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
}

// Returns null when the device is too weak or has no WebGL; the page reads the same without the layer.
export function createSky(canvas, kind) {
  const weak = (navigator.hardwareConcurrency || 4) <= 2 || (navigator.deviceMemory || 4) <= 2;
  if (weak) return null;
  const gl = canvas.getContext("webgl", { antialias: true, alpha: true, premultipliedAlpha: true, depth: false,
    stencil: false, powerPreference: "low-power" });
  if (!gl) return null;
  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  if (!vs || !fs) return null;
  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
  gl.useProgram(program);

  const conf = KINDS[kind] || petals;
  const phone = matchMedia("(max-width: 859px)").matches;
  const total = Math.round(conf.count * (phone ? 0.55 : 1));
  const seeds = new Float32Array(total * 4);
  const more = new Float32Array(total * 2);
  let s = 1234567;
  const rand = () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
  for (let i = 0; i < total; i++) {
    seeds.set([rand(), rand(), Math.pow(rand(), 1.6), rand()], i * 4);
    more.set([rand(), i / total], i * 2);
  }
  const attr = (name, data, size) => {
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(program, name);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  };
  attr("aSeed", seeds, 4);
  attr("aMore", more, 2);
  const u = {};
  for (const name of ["uView", "uTime", "uWind", "uScroll", "uDensity", "uDpr", "uSize", "uFall", "uSway", "uAlpha",
    "uSpin", "uFlip", "uC1", "uC2", "uC3", "uShape"]) u[name] = gl.getUniformLocation(program, name);
  gl.uniform2f(u.uSize, conf.size[0], conf.size[1]);
  gl.uniform2f(u.uFall, conf.fall[0], conf.fall[1]);
  gl.uniform2f(u.uSway, conf.sway[0], conf.sway[1]);
  gl.uniform2f(u.uAlpha, conf.alpha[0], conf.alpha[1]);
  gl.uniform1f(u.uSpin, conf.spin);
  gl.uniform1f(u.uFlip, conf.flip);
  gl.uniform1f(u.uShape, conf.shape);
  gl.enable(gl.BLEND);

  const readColors = () => {
    const css = getComputedStyle(document.documentElement);
    gl.uniform3fv(u.uC1, hexColor(css.getPropertyValue("--particle-1")));
    gl.uniform3fv(u.uC2, hexColor(css.getPropertyValue("--particle-2")));
    gl.uniform3fv(u.uC3, hexColor(css.getPropertyValue("--particle-3")));
    const add = css.getPropertyValue("--particle-blend").trim() === "add";
    gl.blendFunc(gl.ONE, add ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA);
  };
  readColors();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", readColors);

  let dpr = 1;
  const resize = () => {
    dpr = Math.min(window.devicePixelRatio || 1, phone ? 1.5 : 2);
    const w = window.innerWidth;
    const h = window.innerHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform2f(u.uView, w, h);
    gl.uniform1f(u.uDpr, dpr);
  };
  resize();

  let lost = false;
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); lost = true; });

  let wind = 0;
  let last = 0;
  let drawn = total;
  let slow = 0;
  return {
    resize,
    // now: ms; scrollY: px; velocity: px a second; density: 0 to 1 of the particles shown.
    frame(now, scrollY, velocity, density) {
      if (lost) return;
      const t = now / 1000;
      const dt = last ? Math.min(t - last, 0.1) : 0;
      last = t;
      if (dt > 0.026 && t > 3) slow++;
      else if (slow > 0) slow -= 0.25;
      if (slow > 40 && drawn > total / 4) { drawn = Math.round(drawn / 2); slow = 0; }
      const gust = conf.wind * (1 + 0.8 * Math.sin(t * 0.37) + 0.5 * Math.sin(t * 0.13 + 1.7));
      wind += (gust - velocity * 0.06) * dt;
      gl.uniform1f(u.uTime, t);
      gl.uniform1f(u.uWind, wind);
      gl.uniform1f(u.uScroll, scrollY);
      gl.uniform1f(u.uDensity, density * (drawn / total));
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.POINTS, 0, total);
    },
  };
}
