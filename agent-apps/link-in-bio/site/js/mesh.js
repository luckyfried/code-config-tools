// The mesh-gradient stage: four color blobs from the theme drifting through simplex noise, laid on like pigment
// in a light theme and added like light in a dark one.
// Renders into a small canvas that CSS scales up; a gradient this soft needs no more pixels.

const VERTEX = `
attribute vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }
`;

const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 uRes;
uniform float uTime;
uniform vec2 uLean;
uniform vec3 uC1;
uniform vec3 uC2;
uniform vec3 uC3;
uniform vec3 uC4;
uniform vec3 uBase;
uniform float uGlow;

vec3 permute(vec3 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 a0 = x - floor(x + 0.5);
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g = vec3(a0.x * x0.x + h.x * x0.y, a0.yz * x12.xz + h.yz * x12.yw);
  return 130.0 * dot(m, g);
}

float blob(vec2 p, vec2 c, float r) {
  vec2 d = p - c;
  return exp(-dot(d, d) / (r * r));
}

vec2 drift(float seed, float t) {
  return vec2(snoise(vec2(t, seed)), snoise(vec2(seed + 17.0, t)));
}

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  float aspect = uRes.x / uRes.y;
  vec2 s = vec2(aspect, 1.0);
  vec2 p = uv * s;
  float t = uTime * 0.075;

  vec2 warp = vec2(snoise(p * 1.6 + vec2(t, -t * 0.8)), snoise(p * 1.6 + vec2(-t * 0.7, t) + 9.1));
  p += warp * 0.12;

  float r = 0.32 + 0.08 * min(aspect, 2.0);
  vec2 lean = uLean * 0.06;
  float w1 = blob(p, (vec2(0.26, 0.74) + 0.34 * drift(1.3, t)) * s + lean, r);
  float w2 = blob(p, (vec2(0.76, 0.70) + 0.34 * drift(4.7, t)) * s + lean, r * 0.9);
  float w3 = blob(p, (vec2(0.30, 0.26) + 0.34 * drift(8.1, t)) * s - lean, r * 1.05);
  float w4 = blob(p, (vec2(0.74, 0.28) + 0.34 * drift(12.9, t)) * s - lean, r * 0.85);

  vec3 l1 = uC1 * uC1;
  vec3 l2 = uC2 * uC2;
  vec3 l3 = uC3 * uC3;
  vec3 l4 = uC4 * uC4;
  vec3 base = uBase * uBase;
  vec3 col;
  if (uGlow > 0.5) {
    // Dark: each blob is light in a dark room, so overlaps add up and bloom.
    col = base + l1 * w1 * 1.15 + l2 * w2 * 1.15 + l3 * w3 * 1.15 + l4 * w4 * 1.15;
    col = col / (1.0 + col * 0.35);
    col *= 1.0 - 0.55 * smoothstep(0.35, 1.05, length((uv - 0.5) * vec2(1.0, 1.15)));
  } else {
    // Light: pigment laid over paper, one wash on another, with a lit sky at the top.
    col = mix(base, l3, w3 * 0.92);
    col = mix(col, l4, w4 * 0.92);
    col = mix(col, l1, w1 * 0.92);
    col = mix(col, l2, w2 * 0.92);
    col += vec3(0.10) * smoothstep(0.35, 1.0, uv.y) * (1.0 - w1 - w2 * 0.5);
    col *= 1.0 - 0.12 * smoothstep(0.45, 1.1, length(uv - vec2(0.5, 0.62)));
  }
  gl_FragColor = vec4(sqrt(max(col, 0.0)), 1.0);
}
`;

const probe = document.createElement("canvas").getContext("2d");

function readColor(styles, name) {
  probe.fillStyle = "#000000";
  probe.fillStyle = styles.getPropertyValue(name).trim() || "#000000";
  const value = probe.fillStyle;
  if (value.startsWith("#")) {
    return [1, 3, 5].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
  }
  const parts = value.match(/[\d.]+/g) || ["0", "0", "0"];
  return parts.slice(0, 3).map((n) => Number(n) / 255);
}

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
}

// Starts the stage. Returns false when WebGL is not there, so the page keeps its still gradient.
export function startMesh(canvas, { still = false } = {}) {
  if (!canvas) return false;
  let gl = null;
  try {
    gl = canvas.getContext("webgl", { antialias: false, alpha: false, depth: false, stencil: false, powerPreference: "low-power" });
  } catch {
    gl = null;
  }
  if (!gl) return false;

  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  if (!vs || !fs) return false;
  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return false;
  gl.useProgram(program);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(program, "aPos");
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const u = Object.fromEntries(["uRes", "uTime", "uLean", "uC1", "uC2", "uC3", "uC4", "uBase", "uGlow"].map((n) => [n, gl.getUniformLocation(program, n)]));

  const setColors = () => {
    const styles = getComputedStyle(document.documentElement);
    ["uC1", "uC2", "uC3", "uC4"].forEach((name, i) => gl.uniform3fv(u[name], readColor(styles, `--blob-${i + 1}`)));
    gl.uniform3fv(u.uBase, readColor(styles, "--stage-base"));
    gl.uniform1f(u.uGlow, Number(styles.getPropertyValue("--stage-glow")) || 0);
  };

  const resize = () => {
    const w = Math.max(48, Math.round(window.innerWidth / 5));
    const h = Math.max(48, Math.round(window.innerHeight / 5));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    }
    gl.uniform2f(u.uRes, w, h);
  };

  let lean = [0, 0];
  let leanTarget = [0, 0];
  window.addEventListener("pointermove", (e) => {
    leanTarget = [(e.clientX / window.innerWidth) * 2 - 1, 1 - (e.clientY / window.innerHeight) * 2];
  }, { passive: true });

  let ready = false;
  const draw = (seconds) => {
    lean = [lean[0] + (leanTarget[0] - lean[0]) * 0.04, lean[1] + (leanTarget[1] - lean[1]) * 0.04];
    gl.uniform1f(u.uTime, seconds);
    gl.uniform2f(u.uLean, lean[0], lean[1]);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    if (!ready) {
      ready = true;
      document.documentElement.classList.add("gl-ready");
    }
  };

  setColors();
  resize();
  window.addEventListener("resize", () => { resize(); if (still) draw(24); }, { passive: true });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { setColors(); if (still) draw(24); });

  canvas.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    document.documentElement.classList.remove("gl-ready");
    document.documentElement.classList.add("no-gl");
  });

  if (still) {
    draw(24);
    return true;
  }

  // A fixed offset into the noise picks a composed opening frame instead of the noise origin.
  const start = performance.now() - 24000;
  const frame = (now) => {
    if (!document.hidden) draw((now - start) / 1000);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  return true;
}
