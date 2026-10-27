// The spotlight: a soft open cone from above with dust drifting inside it. It drops onto a poster from the top down,
// strikes with a short flicker, and follows that poster as the wall glides.
import { Group, Mesh, CylinderGeometry, Points, BufferGeometry, Float32BufferAttribute } from "three";
import { coneMaterial, dustMaterial, setBlend } from "./materials.js";

const HEIGHT = 5.6;
const TOP_R = 0.08;
const BOTTOM_R = 1.3;

export class Spotlight {
  constructor(scene, count) {
    this.group = new Group();
    this.cone = new Mesh(new CylinderGeometry(TOP_R, BOTTOM_R, HEIGHT, 72, 1, true), coneMaterial(HEIGHT));
    this.cone.renderOrder = 4;
    const seeds = new Float32Array(count * 4);
    for (let i = 0; i < count; i += 1) {
      seeds[i * 4] = Math.random();
      seeds[i * 4 + 1] = Math.random() * Math.PI * 2;
      seeds[i * 4 + 2] = Math.sqrt(Math.random());
      seeds[i * 4 + 3] = Math.random();
    }
    const geo = new BufferGeometry();
    geo.setAttribute("position", new Float32BufferAttribute(new Float32Array(count * 3), 3));
    geo.setAttribute("aSeed", new Float32BufferAttribute(seeds, 4));
    this.dust = new Points(geo, dustMaterial(HEIGHT, TOP_R, BOTTOM_R));
    this.dust.frustumCulled = false;
    this.dust.renderOrder = 5;
    this.group.add(this.cone, this.dust);
    this.group.position.y = HEIGHT / 2;
    scene.add(this.group);
  }

  setTokens(t) {
    const additive = t.additive > 0.5;
    this.cone.material.uniforms.uColor.value.copy(t.beam);
    this.cone.material.uniforms.uStrength.value = t.beamStrength;
    this.dust.material.uniforms.uColor.value.copy(t.dust);
    setBlend(this.cone.material, additive);
    setBlend(this.dust.material, additive);
  }

  setPixel(ratio) {
    this.dust.material.uniforms.uPixel.value = ratio;
  }

  update(time, at, level, drop) {
    this.group.position.x = at.x;
    this.group.position.z = at.z + 0.1;
    this.group.visible = level > 0.001;
    const c = this.cone.material.uniforms;
    c.uLevel.value = level;
    c.uDrop.value = drop;
    const d = this.dust.material.uniforms;
    d.uTime.value = time;
    d.uLevel.value = level;
    d.uDrop.value = drop;
  }
}
