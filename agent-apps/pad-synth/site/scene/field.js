// The full-window wave field, WebGL2 with no library. createField answers null when WebGL2 is missing or a
// shader will not build, and the page falls back to CSS glows.
import { FIELD, MAX, TRAIL, VERTEX } from "./shaders.js";
import { Adapt } from "./quality.js";

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.warn(gl.getShaderInfoLog(shader));
    return null;
  }
  return shader;
}

function program(gl, fragment) {
  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fs = compile(gl, gl.FRAGMENT_SHADER, fragment);
  if (!vs || !fs) return null;
  const made = gl.createProgram();
  gl.attachShader(made, vs);
  gl.attachShader(made, fs);
  gl.linkProgram(made);
  if (!gl.getProgramParameter(made, gl.LINK_STATUS)) {
    console.warn(gl.getProgramInfoLog(made));
    return null;
  }
  const uniforms = {};
  const count = gl.getProgramParameter(made, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < count; i += 1) {
    const name = gl.getActiveUniform(made, i).name.replace(/\[0\]$/, "");
    uniforms[name] = gl.getUniformLocation(made, name);
  }
  return { made, uniforms };
}

/** Wavenumber for a frequency: about 0.075 of the short side per wave at middle C, shorter as pitch rises. */
function wavenumber(freq) {
  const length = Math.max(0.03, 0.075 * (262 / freq) ** 0.55);
  return (2 * Math.PI) / Math.min(0.16, length);
}

export function createField(canvas, { tier, reduced }) {
  const gl = canvas.getContext("webgl2", {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    premultipliedAlpha: false,
    powerPreference: "high-performance",
  });
  if (!gl) return null;
  const trailProgram = program(gl, TRAIL);
  const fieldProgram = program(gl, FIELD);
  if (!trailProgram || !fieldProgram) return null;

  const floats = Boolean(gl.getExtension("EXT_color_buffer_float"));
  const vao = gl.createVertexArray();
  const adapt = new Adapt(tier);
  const src = new Float32Array(MAX * 4);
  const col = new Float32Array(MAX * 4);
  let palette = { bg: [0, 0, 0], a: [1, 1, 1], b: [1, 1, 1], light: false };
  let targets = [];
  let trailSize = [1, 1];
  let current = 0;
  let lost = false;

  function target(width, height) {
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    if (floats) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, width, height, 0, gl.RGBA, gl.HALF_FLOAT, null);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const buffer = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, buffer);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { texture, buffer };
  }

  function resize() {
    const width = Math.max(1, Math.round(window.innerWidth * adapt.scale));
    const height = Math.max(1, Math.round(window.innerHeight * adapt.scale));
    canvas.width = width;
    canvas.height = height;
    const tw = Math.max(1, Math.round(window.innerWidth * adapt.trail));
    const th = Math.max(1, Math.round(window.innerHeight * adapt.trail));
    if (tw !== trailSize[0] || th !== trailSize[1] || targets.length === 0) {
      for (const old of targets) {
        gl.deleteTexture(old.texture);
        gl.deleteFramebuffer(old.buffer);
      }
      targets = [target(tw, th), target(tw, th)];
      trailSize = [tw, th];
    }
  }

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    lost = true;
    document.documentElement.classList.add("no-gl");
  });

  resize();

  return {
    resize,
    get lost() {
      return lost;
    },
    setPalette(tokens) {
      palette = { bg: tokens.bg.slice(0, 3), a: tokens.a.slice(0, 3), b: tokens.b.slice(0, 3), light: tokens.light };
    },
    /** Draws one frame: `now` in seconds, `dt` since the last frame, `sources` the Sources list. */
    frame(now, dt, sources, frameMs) {
      if (lost) return;
      if (adapt.frame(frameMs)) resize();
      const list = sources.list;
      const count = Math.min(list.length, MAX);
      for (let i = 0; i < count; i += 1) {
        const s = list[i];
        src[i * 4] = s.x;
        src[i * 4 + 1] = 1 - s.y;
        src[i * 4 + 2] = s.born;
        src[i * 4 + 3] = wavenumber(s.freq);
        col[i * 4] = s.color[0];
        col[i * 4 + 1] = s.color[1];
        col[i * 4 + 2] = s.color[2];
        col[i * 4 + 3] = Math.min(1.4, s.amp);
      }
      const short = Math.min(window.innerWidth, window.innerHeight);
      const scale = [window.innerWidth / short, window.innerHeight / short];
      const motion = reduced ? 0 : 1;
      const time = now % 3600;
      // Times are sent relative to the hour so the shader's floats keep their precision.
      for (let i = 0; i < count; i += 1) src[i * 4 + 2] = list[i].born - (now - time);

      gl.bindVertexArray(vao);
      const next = 1 - current;
      gl.bindFramebuffer(gl.FRAMEBUFFER, targets[next].buffer);
      gl.viewport(0, 0, trailSize[0], trailSize[1]);
      gl.useProgram(trailProgram.made);
      let u = trailProgram.uniforms;
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, targets[current].texture);
      gl.uniform1i(u.uPrev, 0);
      gl.uniform2f(u.uRes, trailSize[0], trailSize[1]);
      gl.uniform2f(u.uScale, scale[0], scale[1]);
      gl.uniform1f(u.uTime, time);
      gl.uniform1f(u.uDecay, Math.exp(-dt / (reduced ? 0.6 : 1.25)));
      gl.uniform1f(u.uDrift, reduced ? 0 : dt * 0.045);
      gl.uniform1f(u.uEmit, Math.min(dt, 0.05) * 0.65);
      gl.uniform1f(u.uMotion, motion);
      gl.uniform1i(u.uCount, count);
      gl.uniform4fv(u.uSrc, src);
      gl.uniform4fv(u.uCol, col);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      current = next;

      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(fieldProgram.made);
      u = fieldProgram.uniforms;
      gl.bindTexture(gl.TEXTURE_2D, targets[current].texture);
      gl.uniform1i(u.uTrail, 0);
      gl.uniform2f(u.uRes, canvas.width, canvas.height);
      gl.uniform2f(u.uScale, scale[0], scale[1]);
      gl.uniform1f(u.uTime, time);
      gl.uniform1f(u.uMotion, motion);
      gl.uniform1f(u.uMode, palette.light ? 1 : 0);
      gl.uniform3fv(u.uBg, palette.bg);
      gl.uniform3fv(u.uA, palette.a);
      gl.uniform3fv(u.uB, palette.b);
      gl.uniform1i(u.uCount, count);
      gl.uniform4fv(u.uSrc, src);
      gl.uniform4fv(u.uCol, col);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
  };
}
