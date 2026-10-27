// The studio: an HDR environment for the lacquer's reflections and one key light that throws the disc shadows and
// catches every flip.
import { DirectionalLight, PMREMGenerator, EquirectangularReflectionMapping, Color } from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";

export async function loadStudio(renderer, url) {
  const texture = await new HDRLoader().loadAsync(url);
  texture.mapping = EquirectangularReflectionMapping;
  const pmrem = new PMREMGenerator(renderer);
  const target = pmrem.fromEquirectangular(texture);
  texture.dispose();
  pmrem.dispose();
  return target.texture;
}

export function createKeyLight(settings) {
  // High over the table's front left, so the disc stacks throw short shadows straight down into their trays.
  const key = new DirectionalLight(0xffffff, 2.4);
  key.position.set(-4, 20, 5);
  key.target.position.set(0, 0, 0);
  key.castShadow = true;
  key.shadow.mapSize.set(settings.shadowMap, settings.shadowMap);
  const cam = key.shadow.camera;
  cam.left = -11;
  cam.right = 11;
  cam.top = 11;
  cam.bottom = -11;
  cam.near = 4;
  cam.far = 40;
  key.shadow.bias = -0.0008;
  key.shadow.normalBias = 0.045;
  key.shadow.radius = 3;
  return key;
}

export function applyLightTokens(key, tokens) {
  key.intensity = tokens.key;
  key.color = new Color(tokens.keyColor);
}
