// One named material per role, shared by every mesh that plays that part. Colors come from the theme tokens;
// apply() recolors them in place when the color scheme changes.
import {
  AdditiveBlending,
  Color,
  DoubleSide,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Vector2,
} from "three";
import { StrataTexture, chevrons, contactBlob, sandstoneNormal, softDot, swirl, trackDetail } from "./textures.js";

export function createMaterials(tier, tokens, marbleHex) {
  const normal = sandstoneNormal(tier.name === "high" ? 512 : 256);
  const strata = new StrataTexture();
  strata.paint(tokens.rocks);
  const detail = trackDetail();
  const arrows = chevrons();
  const dot = softDot();
  const marbleColor = new Color(marbleHex);

  const rock = new MeshStandardMaterial({
    color: 0xffffff,
    map: strata.texture,
    normalMap: normal,
    normalScale: new Vector2(1.4, 1.4),
    roughness: 0.93,
    metalness: 0,
    vertexColors: true,
    flatShading: tier.flat,
  });

  const track = new MeshStandardMaterial({
    color: tokens.track.clone(),
    map: detail,
    roughness: 0.38,
    metalness: 0,
    envMapIntensity: tokens.trackEnv,
    flatShading: tier.flat,
  });

  const trackSide = new MeshStandardMaterial({
    color: tokens.trackSide.clone(),
    roughness: 0.6,
    metalness: 0.1,
    flatShading: tier.flat,
  });

  const lane = new MeshStandardMaterial({
    color: tokens.lane.clone(),
    emissive: tokens.glow.clone(),
    emissiveIntensity: tokens.glowStrength,
    roughness: 0.35,
  });

  const kerb = new MeshStandardMaterial({ color: 0xffffff, roughness: 0.45, metalness: 0.05 });

  const boost = new MeshStandardMaterial({
    color: tokens.boost.clone(),
    map: arrows,
    emissive: tokens.boost.clone(),
    emissiveMap: arrows,
    emissiveIntensity: 1.1,
    roughness: 0.3,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });

  const gate = new MeshStandardMaterial({
    color: tokens.gate.clone(),
    emissive: tokens.gate.clone(),
    emissiveIntensity: 0.25 + tokens.glowStrength * 0.3,
    roughness: 0.35,
    metalness: 0.3,
  });

  const curtain = new MeshBasicMaterial({
    color: tokens.gate.clone(),
    transparent: true,
    opacity: 0.12,
    blending: AdditiveBlending,
    depthWrite: false,
    side: DoubleSide,
  });

  // High tier: the shell refracts the canyon behind it, the swirl inside is drawn straight (sharp, not through the
  // blurred transmission buffer), and a clear glaze over both carries the reflections and the sun's highlight.
  // Mid and low tiers have no transmission, so the glaze is the shell: clear at the center over the same swirl,
  // a mirror of the canyon toward the rim, and the sun's highlight on top.
  const glaze = new MeshStandardMaterial({
    color: 0xffffff,
    metalness: 1,
    roughness: tier.transmission ? 0.1 : 0.05,
    envMapIntensity: tier.transmission ? 1.2 : 1.35,
    transparent: true,
  });
  // Fresnel: nearly clear where the glass faces the camera, so the swirl stays sharp and saturated, and a
  // mirror of the canyon toward the rim. Without refraction the shell also carries a catchlight up and to the
  // left, the bright window a polished sphere always shows.
  const catchlight = tier.transmission
    ? ""
    : `float glint = pow(max(dot(normal, normalize(vec3(-0.38, 0.5, 0.78))), 0.0), 260.0);
      outgoingLight += vec3(glint * 2.4);
      diffuseColor.a = max(diffuseColor.a, min(1.0, glint * 1.5));`;
  glaze.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <opaque_fragment>",
      `float facing = clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0);
      diffuseColor.a = mix(0.1, 0.85, pow(1.0 - facing, 2.5));
      ${catchlight}
      #include <opaque_fragment>`,
    );
  };

  const glass = tier.transmission
    ? new MeshPhysicalMaterial({
        color: 0xffffff,
        transmission: 1,
        thickness: 0.9,
        ior: 1.5,
        roughness: 0,
        metalness: 0,
        attenuationColor: marbleColor.clone().lerp(new Color(0xffffff), 0.86),
        attenuationDistance: 3,
        specularIntensity: 0,
        depthWrite: false,
      })
    : glaze;

  const swirlMaterial = new MeshStandardMaterial({
    map: swirl(marbleHex),
    alphaTest: 0.35,
    transparent: tier.transmission,
    side: DoubleSide,
    roughness: 0.25,
    emissive: marbleColor.clone(),
    emissiveIntensity: 0.2,
  });

  const ghost = new MeshStandardMaterial({
    color: tokens.ghost.clone(),
    transparent: true,
    opacity: 0.4,
    roughness: 0.1,
    metalness: 0.25,
    depthWrite: false,
    envMapIntensity: 1.4,
  });
  // The ghost thins toward its center and holds its rim, so the track shows through it on a pale track too.
  ghost.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <opaque_fragment>",
      `float ghostFacing = clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0);
      diffuseColor.a *= mix(0.3, 1.9, pow(1.0 - ghostFacing, 2.0));
      #include <opaque_fragment>`,
    );
  };

  const trail = new MeshBasicMaterial({
    color: tokens.ghost.clone(),
    transparent: true,
    opacity: 0.45,
    depthWrite: false,
    side: DoubleSide,
    vertexColors: true,
  });

  const blob = contactBlob();
  const contact = new MeshBasicMaterial({
    color: 0x000000,
    alphaMap: blob,
    transparent: true,
    opacity: 0.45,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -4,
  });

  // The soft dark patch each boulder sits in, so it reads as resting on the ground.
  const rockShadow = new MeshBasicMaterial({
    color: 0x000000,
    alphaMap: blob,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });

  const pylon = new MeshStandardMaterial({
    color: tokens.trackSide.clone(),
    roughness: 0.7,
    metalness: 0.15,
    flatShading: true,
  });

  const boulder = new MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.95,
    flatShading: true,
    normalMap: normal,
    normalScale: new Vector2(0.8, 0.8),
  });

  const river = new MeshStandardMaterial({
    color: tokens.skyMid.clone().lerp(tokens.fog, 0.35),
    emissive: tokens.glow.clone(),
    emissiveIntensity: tokens.glowStrength * 0.25,
    roughness: 0.08,
    metalness: 0.4,
    envMapIntensity: 1.2,
  });

  const palette = tokens.rocks.map((c) => c.clone());

  return {
    palette,
    rock,
    track,
    trackSide,
    lane,
    kerb,
    boost,
    gate,
    curtain,
    glass,
    glaze,
    swirl: swirlMaterial,
    ghost,
    trail,
    contact,
    rockShadow,
    pylon,
    boulder,
    river,
    textures: { normal, strata, detail, arrows, dot },
    apply(t) {
      strata.paint(t.rocks);
      t.rocks.forEach((c, i) => palette[i].copy(c));
      track.color.copy(t.track);
      track.envMapIntensity = t.trackEnv;
      trackSide.color.copy(t.trackSide);
      pylon.color.copy(t.trackSide);
      lane.color.copy(t.lane);
      lane.emissive.copy(t.glow);
      lane.emissiveIntensity = t.glowStrength;
      boost.color.copy(t.boost);
      boost.emissive.copy(t.boost);
      gate.color.copy(t.gate);
      gate.emissive.copy(t.gate);
      gate.emissiveIntensity = 0.25 + t.glowStrength * 0.3;
      curtain.color.copy(t.gate);
      ghost.color.copy(t.ghost);
      trail.color.copy(t.ghost);
      river.color.copy(t.skyMid).lerp(t.fog, 0.35);
      river.emissive.copy(t.glow);
      river.emissiveIntensity = t.glowStrength * 0.25;
    },
  };
}
