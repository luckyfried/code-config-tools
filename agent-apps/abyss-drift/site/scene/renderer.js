// The WebGL renderer: color space, tone mapping, and the pixel ratio the tier allows.
import * as THREE from "three";

export function createRenderer(canvas, tier) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", alpha: false });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, tier.pixelRatio));
  renderer.setSize(innerWidth, innerHeight, false);
  return renderer;
}
