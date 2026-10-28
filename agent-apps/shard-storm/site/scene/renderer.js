// The WebGL renderer: sRGB output, no tone mapping (the bloom carries the highlights), ratio capped by the tier.
import * as THREE from "three";

export function createRenderer(canvas, tier) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", stencil: false });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, tier.dpr));
  return renderer;
}
