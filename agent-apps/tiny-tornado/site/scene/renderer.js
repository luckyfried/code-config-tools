// The WebGL renderer: pixel ratio, color space, ACES tone mapping, and soft shadows.
import * as THREE from "three";

export function createRenderer(canvas, settings) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: !settings.post, powerPreference: "high-performance", stencil: false });
  renderer.setPixelRatio(settings.ratio);
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = settings.shadowSize > 0;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  return renderer;
}
