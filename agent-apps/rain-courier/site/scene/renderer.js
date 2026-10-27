// The WebGLRenderer: pixel ratio capped at 2, sRGB output, ACES tone mapping.
import * as THREE from "three";

export function createRenderer(canvas, ratio) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", stencil: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, ratio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  return renderer;
}
