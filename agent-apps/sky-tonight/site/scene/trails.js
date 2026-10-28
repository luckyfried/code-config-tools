// Star trails: while time runs fast the stars are also drawn into a half-resolution buffer that keeps the brighter
// of last frame (faded) and this frame, so each star leaves a short streak that dies away within a fraction of a
// second once time slows. The buffer joins the screen through a MAX blend, so the stars themselves stay sharp.
import * as THREE from "three";

const VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = position.xy * 0.5 + 0.5;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

const ACCUMULATE = /* glsl */ `
uniform sampler2D uPrev;
uniform sampler2D uCur;
uniform float uDecay;
varying vec2 vUv;
void main() {
  vec4 prev = texture(uPrev, vUv) * uDecay;
  vec4 cur = texture(uCur, vUv);
  gl_FragColor = max(prev, cur);
}
`;

const COMPOSITE = /* glsl */ `
uniform sampler2D uTex;
uniform float uInkMode;
uniform vec3 uInk;
varying vec2 vUv;
void main() {
  vec4 c = texture(uTex, vUv);
  if (uInkMode > 0.5) {
    gl_FragColor = vec4(uInk, clamp(c.a, 0.0, 1.0));
  } else {
    gl_FragColor = vec4(min(c.rgb * 1.3, vec3(1.0)), 1.0);
  }
}
`;

function fullscreen(material) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  return mesh;
}

export function createTrails(renderer) {
  const options = { depthBuffer: false, stencilBuffer: false, type: THREE.UnsignedByteType };
  let cur = new THREE.WebGLRenderTarget(1, 1, options);
  let a = new THREE.WebGLRenderTarget(1, 1, options);
  let b = new THREE.WebGLRenderTarget(1, 1, options);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const accumulate = new THREE.ShaderMaterial({
    uniforms: { uPrev: { value: null }, uCur: { value: null }, uDecay: { value: 0.9 } },
    vertexShader: VERTEX,
    fragmentShader: ACCUMULATE,
    depthTest: false,
    depthWrite: false,
  });
  const composite = new THREE.ShaderMaterial({
    uniforms: { uTex: { value: null }, uInkMode: { value: 0 }, uInk: { value: new THREE.Vector3() } },
    vertexShader: VERTEX,
    fragmentShader: COMPOSITE,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.CustomBlending,
    blendEquation: THREE.MaxEquation,
    blendSrc: THREE.OneFactor,
    blendDst: THREE.OneFactor,
  });
  const accScene = new THREE.Scene();
  accScene.add(fullscreen(accumulate));
  const compScene = new THREE.Scene();
  compScene.add(fullscreen(composite));
  let primed = false;
  const black = new THREE.Color(0, 0, 0);

  return {
    resize(w, h) {
      w = Math.max(1, Math.round(w / 2));
      h = Math.max(1, Math.round(h / 2));
      cur.setSize(w, h);
      a.setSize(w, h);
      b.setSize(w, h);
      primed = false;
    },
    reset() {
      primed = false;
    },
    // Draws `starScene` into the trail buffer and leaves the composite ready for `drawComposite`.
    accumulate(starScene, decay) {
      const prevTarget = renderer.getRenderTarget();
      renderer.setClearColor(black, 0);
      renderer.setRenderTarget(cur);
      renderer.clear(true, false, false);
      renderer.render(starScene, camera);
      if (!primed) {
        renderer.setRenderTarget(a);
        renderer.clear(true, false, false);
        primed = true;
      }
      accumulate.uniforms.uPrev.value = a.texture;
      accumulate.uniforms.uCur.value = cur.texture;
      accumulate.uniforms.uDecay.value = decay;
      renderer.setRenderTarget(b);
      renderer.render(accScene, camera);
      const t = a; a = b; b = t;
      renderer.setRenderTarget(prevTarget);
    },
    drawComposite() {
      composite.uniforms.uTex.value = a.texture;
      renderer.render(compScene, camera);
    },
    setInk(ink, inkColor) {
      composite.uniforms.uInkMode.value = ink ? 1 : 0;
      composite.uniforms.uInk.value.set(...inkColor);
      composite.blending = ink ? THREE.NormalBlending : THREE.CustomBlending;
      composite.needsUpdate = true;
    },
  };
}
