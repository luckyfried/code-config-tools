// One named look per surface: lacquered discs, the board's face and frame, the trays, the table, and the marks.
import { MeshPhysicalMaterial, MeshStandardMaterial, MeshBasicMaterial, Color, Vector3, AdditiveBlending, NormalBlending } from "three";

/**
 * The key light's glint on the disc lacquer: the face direction (view space, set by the scene each frame) that sends
 * the key light to the eye. Where a disc's surface turns that way, its clearcoat shows the glint.
 */
export const glintFace = { value: new Vector3(0, 1, 0) };

/**
 * Double-sided lacquer: clearcoat 1 over a tinted base, with a faint color-shifting sheen, and the key light's crisp
 * glint on the clearcoat. The glint is the disc's own: it lands on the domed face where the face turns the key toward
 * the eye, so every disc carries one, and it slides across a disc as the disc turns.
 */
export function discMaterial(settings, strength, depth) {
  const glintStrength = { value: strength };
  const glintDepth = { value: depth };
  const glintBase = { value: 1 };
  const material = new MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.32,
    metalness: 0,
    clearcoat: 1,
    clearcoatRoughness: 0.05,
    sheen: 0.45,
    sheenRoughness: 0.32,
    sheenColor: new Color(0xcfe0ff),
    iridescence: settings.iridescence ? 0.16 : 0,
    iridescenceIOR: 1.35,
    iridescenceThicknessRange: [180, 420],
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.glintFace = glintFace;
    shader.uniforms.glintStrength = glintStrength;
    shader.uniforms.glintDepth = glintDepth;
    shader.uniforms.glintBase = glintBase;
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 glintFace;\nuniform float glintStrength;\nuniform float glintDepth;\nuniform float glintBase;")
      .replace(
        "#include <opaque_fragment>",
        [
          "float glintNH = saturate( dot( normal, glintFace ) );",
          // Lacquer depth: under a bright room a light face sits a step under white (`glintBase`) so the glint reads
          // over it, and every face dims a little as it turns away from the glint, most at the rim.
          "outgoingLight *= glintBase * ( 1.0 - glintDepth * ( 1.0 - pow( glintNH, 140.0 ) ) );",
          "outgoingLight += glintStrength * ( pow( glintNH, 2400.0 ) + 0.03 * pow( glintNH, 300.0 ) );",
          "#include <opaque_fragment>",
        ].join("\n"),
      );
  };
  material.customProgramCacheKey = () => "disc-glint";
  material.glintStrength = glintStrength;
  material.glintBase = glintBase;
  return material;
}

export function lacquerMaterial() {
  return new MeshPhysicalMaterial({ color: 0x111111, roughness: 0.3, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.06 });
}

export function boardFaceMaterial() {
  return new MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.42,
    metalness: 0,
    clearcoat: 1,
    clearcoatRoughness: 0.07,
    emissive: 0xffffff,
    emissiveIntensity: 0,
  });
}

export function feltMaterial() {
  return new MeshStandardMaterial({ color: 0x0b3a29, roughness: 0.96, metalness: 0 });
}

export function tableMaterial() {
  return new MeshStandardMaterial({ color: 0xffffff, roughness: 0.82, metalness: 0 });
}

/**
 * A mark material whose instances each carry their own opacity (the `instanceAlpha` attribute), for the legal dots,
 * the preview tint, and the reduced-motion cross-fade.
 */
export function instanceAlphaMaterial(base) {
  base.transparent = true;
  base.depthWrite = false;
  base.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute float instanceAlpha;\nvarying float vInstanceAlpha;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvInstanceAlpha = instanceAlpha;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying float vInstanceAlpha;")
      .replace("#include <dithering_fragment>", "#include <dithering_fragment>\ngl_FragColor.a *= vInstanceAlpha;");
  };
  base.customProgramCacheKey = () => `instance-alpha-${base.type}`;
  return base;
}

export function glowMaterial(map) {
  return new MeshBasicMaterial({ map, color: 0xffffff, transparent: true, depthWrite: false, toneMapped: false });
}

export function setGlowBlend(material, additive) {
  material.blending = additive ? AdditiveBlending : NormalBlending;
  material.needsUpdate = true;
}
