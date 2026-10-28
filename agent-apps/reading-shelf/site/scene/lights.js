// Reading-room light: a soft room environment, a sky-and-floor fill, a warm key from above (sun through a window by
// day, a lamp pool at night), and two brass floor lamps with a wash of light on the wall either side of the case.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { windowCanvas, poolCanvas, glowCanvas, scallopCanvas } from "./textures.js";
import { canvasTexture } from "./renderer.js";
import { brass } from "./materials.js";

// How far the lamps stand out from the wall, from their group's origin on the wall.
const LAMP_Z = 0.12;

export function createLights(scene, renderer, settings, tokens) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  scene.environment = envTex;
  scene.environmentIntensity = tokens.env;

  const hemi = new THREE.HemisphereLight(tokens.ambient, tokens.ground, tokens.hemi);
  scene.add(hemi);

  const key = new THREE.SpotLight(tokens.key, tokens.keyPower, 0, 0.5, 0.75, 2);
  const windowMap = canvasTexture(windowCanvas(), renderer);
  const poolMap = canvasTexture(poolCanvas(), renderer);
  key.map = tokens.window > 0.5 ? windowMap : poolMap;
  key.castShadow = settings.shadows;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.0002;
  key.shadow.normalBias = 0.012;
  key.shadow.radius = 4;
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 8;
  scene.add(key, key.target);

  const glowTex = canvasTexture(glowCanvas(), renderer);
  const scallopTex = canvasTexture(scallopCanvas(), renderer);
  const lamps = new THREE.Group();
  const fixtures = [];
  const brassMat = brass();
  const bulbMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(tokens.glow).lerp(new THREE.Color("#fff6e4"), 0.6) });
  const shadeMat = new THREE.MeshStandardMaterial({ color: "#efe3c8", roughness: 0.6, emissive: new THREE.Color(tokens.glow), emissiveIntensity: tokens.glowPower * 1.2, side: THREE.DoubleSide });
  for (const side of [-1, 1]) {
    const f = new THREE.Group();
    // A brass floor lamp standing just off the wall: a weighted foot, a slim stem with a knuckle, a socket collar under
    // the shade, a finial on top, and a warm bulb under the rim. The stem's length is set by place() from the floor.
    const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.052, 0.06, 0.012, 40), brassMat);
    const footDome = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.03, 0.022, 28), brassMat);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.0055, 0.0055, 1, 14), brassMat);
    const knuckle = new THREE.Mesh(new THREE.SphereGeometry(0.0105, 18, 12), brassMat);
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.009, 0.026, 18), brassMat);
    collar.position.set(0, -0.034, LAMP_Z);
    const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.07, 0.1, 28, 1, true), shadeMat);
    shade.position.set(0, 0.03, LAMP_Z);
    const finial = new THREE.Mesh(new THREE.SphereGeometry(0.009, 16, 10), brassMat);
    finial.position.set(0, 0.091, LAMP_Z);
    const spider = new THREE.Mesh(new THREE.CylinderGeometry(0.0025, 0.0025, 0.012, 8), brassMat);
    spider.position.set(0, 0.083, LAMP_Z);
    for (const m of [foot, footDome, stem, knuckle, collar, shade, finial]) m.castShadow = settings.shadows;
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.022, 20, 12), bulbMat);
    cap.position.set(0, -0.004, LAMP_Z);
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: tokens.glow, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.55 * tokens.glowPower }));
    glow.scale.set(0.5, 0.5, 1);
    glow.position.set(0, 0.03, LAMP_Z + 0.02);
    // Light thrown on the wall, up through the open top and down past the rim, brightest at the shade.
    const scallopMat = new THREE.MeshBasicMaterial({ map: scallopTex, color: tokens.glow, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.32 * tokens.glowPower });
    const wash = new THREE.Mesh(new THREE.PlaneGeometry(0.44, 1.5), scallopMat);
    wash.position.set(0, 0.06, 0.002);
    const parts = [foot, footDome, stem, knuckle, collar, shade, spider, finial, cap, glow, wash];
    f.add(...parts);
    let light = null;
    if (settings.lamps) {
      light = new THREE.PointLight(tokens.glow, 0.9 * tokens.glowPower, 2.2, 2);
      light.position.set(0, 0, LAMP_Z + 0.06);
      f.add(light);
    }
    fixtures.push({ group: f, side, glow, scallopMat, light, foot, footDome, stem, knuckle, parts });
    lamps.add(f);
  }
  scene.add(lamps);

  function place(geo, center) {
    const daylight = key.map === windowMap;
    if (daylight) {
      key.position.set(center.x + 2.3, center.y + 2.4, 2.6);
      key.angle = 0.52;
      key.penumbra = 0.35;
    } else {
      key.position.set(center.x - 1.5, center.y + 2.5, 2.4);
      key.angle = 0.5;
      key.penumbra = 0.8;
    }
    key.target.position.set(center.x, center.y - 0.05, 0);
    key.target.updateMatrixWorld();
    const shadeY = geo.topY - 0.32;
    for (const f of fixtures) {
      f.group.position.set(f.side * (geo.outerW / 2 + 0.28), shadeY, -0.13);
      // The stem runs from the foot on the floor to the socket collar under the shade.
      const bottom = -shadeY + 0.018;
      const top = -0.047;
      f.foot.position.set(0, -shadeY + 0.006, LAMP_Z);
      f.footDome.position.set(0, -shadeY + 0.023, LAMP_Z);
      f.stem.scale.y = top - bottom;
      f.stem.position.set(0, (top + bottom) / 2, LAMP_Z);
      f.knuckle.position.set(0, bottom + (top - bottom) * 0.42, LAMP_Z);
    }
  }

  function apply(t, tier) {
    scene.environmentIntensity = t.env;
    hemi.color.set(t.ambient);
    hemi.groundColor.set(t.ground);
    hemi.intensity = t.hemi;
    key.color.set(t.key);
    key.intensity = t.keyPower;
    key.map = t.window > 0.5 ? windowMap : poolMap;
    bulbMat.color.set(t.glow).lerp(new THREE.Color("#fff6e4"), 0.6);
    shadeMat.emissive.set(t.glow);
    shadeMat.emissiveIntensity = t.glowPower * 1.2;
    for (const f of fixtures) {
      f.glow.material.color.set(t.glow);
      f.glow.material.opacity = 0.55 * t.glowPower;
      f.scallopMat.color.set(t.glow);
      f.scallopMat.opacity = 0.32 * t.glowPower;
      if (f.light) {
        f.light.color.set(t.glow);
        f.light.intensity = 0.9 * t.glowPower;
      }
    }
    renderer.toneMappingExposure = t.exposure;
    void tier;
  }

  /** Row views frame the case alone, so the fixtures step out of shot and only their light stays. */
  function showFixtures(on) {
    for (const f of fixtures) f.parts.forEach((m) => (m.visible = on));
  }

  return { hemi, key, lamps, place, apply, showFixtures, daylight: () => key.map === windowMap };
}
