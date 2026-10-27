// The WebGL renderer: color space and filmic tone mapping (bright gold rolls off to white-hot). No shadow maps: the
// cubes stand in their etched sockets and the lit ones spill a soft pool of light, so no hard edge ever cuts across a
// neighbor.
import * as THREE from "three";

export function createRenderer(canvas, tier) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", stencil: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, tier.ratio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = false;
  return renderer;
}
