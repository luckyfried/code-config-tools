// The environment the glass refracts and reflects: the theme's 1K .hdr through the PMREM generator. Until it
// arrives, the sky dome itself stands in, so the marble is never dull on the first frame.
import { EquirectangularReflectionMapping, PMREMGenerator, Scene } from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";

export class Environment {
  constructor(renderer, scene) {
    this.renderer = renderer;
    this.scene = scene;
    this.pmrem = new PMREMGenerator(renderer);
    this.target = null;
    this.name = null;
    this.loader = new HDRLoader();
  }

  fromSky(skyMesh) {
    const holder = new Scene();
    const copy = skyMesh.clone();
    copy.position.set(0, 0, 0);
    holder.add(copy);
    this.swap(this.pmrem.fromScene(holder, 0.02, 0.1, 1100));
  }

  async load(name) {
    if (this.name === name) return;
    this.name = name;
    try {
      const texture = await this.loader.loadAsync(`./env/${name}.hdr`);
      if (this.name !== name) {
        texture.dispose();
        return;
      }
      texture.mapping = EquirectangularReflectionMapping;
      this.swap(this.pmrem.fromEquirectangular(texture));
      texture.dispose();
    } catch {
      // The sky-made environment stays in place.
    }
  }

  swap(target) {
    if (this.target) this.target.dispose();
    this.target = target;
    this.scene.environment = target.texture;
  }
}
