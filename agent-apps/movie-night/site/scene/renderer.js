// The WebGL renderer: the tier's pixel ratio, sRGB output, and no tone mapping, so the theme's colors land as written.
import { WebGLRenderer, SRGBColorSpace, NoToneMapping } from "three";

export function createRenderer(canvas, tier) {
  const renderer = new WebGLRenderer({ canvas, antialias: tier.antialias, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(tier.ratio);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NoToneMapping;
  renderer.sortObjects = true;
  return renderer;
}
