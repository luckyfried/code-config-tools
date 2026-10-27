// The post stack, built by tier. Desktop: depth of field on the drone, bloom, drops on the lens, output.
// Mid: bloom at half resolution, output. Low: none; the renderer draws straight to the screen.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";

const LensDropsShader = {
  name: "LensDrops",
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uAspect: { value: 1 },
    uAmount: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uAspect;
    uniform float uAmount;
    varying vec2 vUv;
    float h21(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    // One drop per grid cell at most: its normal bends the frame like a small lens.
    vec3 drops(vec2 uv, float cols, float t, float rate) {
      vec2 g = vec2(uv.x * uAspect, uv.y) * cols;
      vec2 cell = floor(g);
      vec2 f = fract(g) - 0.5;
      float h = h21(cell);
      float life = fract(t * rate + h * 7.0);
      float present = step(0.8, h21(cell + 13.1)) * smoothstep(0.0, 0.05, life) * smoothstep(1.0, 0.7, life);
      vec2 c = (vec2(h21(cell + 1.7), h21(cell + 4.3)) - 0.5) * 0.5;
      float r = mix(0.1, 0.24, h21(cell + 9.2));
      vec2 d = f - c;
      d.y *= 1.15;
      float l = length(d);
      float inside = smoothstep(r, r * 0.8, l) * present;
      return vec3(d / r, inside);
    }
    vec3 slider(vec2 uv, float t) {
      float cols = 7.0;
      float x = uv.x * uAspect * cols;
      float col = floor(x);
      float h = h21(vec2(col, 3.0));
      float y = fract(uv.y * 0.6 + t * (0.05 + h * 0.08) + h);
      vec2 d = vec2(fract(x) - 0.5 - (h - 0.5) * 0.4, (y - 0.5) * 4.0);
      float r = 0.22;
      float l = length(d);
      float inside = smoothstep(r, r * 0.75, l) * step(0.7, h);
      return vec3(d / r, inside);
    }
    void main() {
      vec3 a = drops(vUv, 26.0, uTime, 0.11);
      vec3 b = drops(vUv + 0.37, 14.0, uTime, 0.07);
      vec3 s = slider(vUv, uTime);
      vec2 n = a.xy * a.z + b.xy * b.z + s.xy * s.z;
      float mask = clamp(a.z + b.z + s.z, 0.0, 1.0) * uAmount;
      vec3 base = texture2D(tDiffuse, vUv).rgb;
      // Inside a drop the frame is bent and a little softened; the top edge catches a highlight.
      vec2 uv = vUv + n * 0.012;
      vec3 bent = (texture2D(tDiffuse, uv).rgb * 2.0 + texture2D(tDiffuse, uv + vec2(0.002, 0.0)).rgb + texture2D(tDiffuse, uv - vec2(0.0, 0.002)).rgb) * 0.25;
      vec3 col = mix(base, bent * 1.08, mask * 0.85);
      col += vec3(0.5) * mask * smoothstep(0.7, 0.95, n.y) * 0.06;
      gl_FragColor = vec4(col, 1.0);
    }
  `,
};

export function createPost({ renderer, scene, camera, tier, width, height, depthHidden }) {
  if (tier === "low") return null;
  const target = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType, samples: tier === "high" ? 4 : 0 });
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));

  let bokeh = null;
  if (tier === "high") {
    bokeh = new BokehPass(scene, camera, { focus: 9, aperture: 0.00009, maxblur: 0.005 });
    // The depth render sees only solid geometry; sprites, rain, and the mirror street stay out of it.
    const render = bokeh.render.bind(bokeh);
    bokeh.render = (r, w, rb, dt, mask) => {
      const hidden = depthHidden.filter((o) => o.visible);
      hidden.forEach((o) => (o.visible = false));
      const original = bokeh._fsQuad.render.bind(bokeh._fsQuad);
      bokeh._fsQuad.render = (rr) => {
        hidden.forEach((o) => (o.visible = true));
        original(rr);
      };
      render(r, w, rb, dt, mask);
      bokeh._fsQuad.render = original;
      hidden.forEach((o) => (o.visible = true));
    };
    composer.addPass(bokeh);
  }

  const half = tier === "mid";
  const bloom = new UnrealBloomPass(new THREE.Vector2(width, height), 0.9, 0.6, 0.82);
  if (half) {
    const setSize = bloom.setSize.bind(bloom);
    bloom.setSize = (w, h) => setSize(Math.max(1, Math.round(w / 2)), Math.max(1, Math.round(h / 2)));
  }
  composer.addPass(bloom);

  let drops = null;
  if (tier === "high") {
    drops = new ShaderPass(LensDropsShader);
    composer.addPass(drops);
  }
  composer.addPass(new OutputPass());
  composer.setSize(width, height);

  return {
    composer,
    bloom,
    setSize(w, h) {
      composer.setSize(w, h);
      if (drops) drops.uniforms.uAspect.value = w / h;
      if (bokeh) bokeh.uniforms.aspect.value = w / h;
    },
    setPixelRatio(ratio) {
      composer.setPixelRatio(ratio);
    },
    update(time, focusDistance, palette, dropsAmount) {
      bloom.strength = palette.bloom;
      if (bokeh) bokeh.uniforms.focus.value = focusDistance;
      if (drops) {
        drops.uniforms.uTime.value = time;
        drops.uniforms.uAmount.value = dropsAmount;
      }
    },
    render(dt) {
      composer.render(dt);
    },
  };
}
