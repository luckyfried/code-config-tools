// The room around the wall: a floor that holds the reflections and the spotlight's pool, and the backdrop behind,
// which is velvet curtains, a night sky, or paper, as the theme says.
import { Mesh, PlaneGeometry } from "three";
import { floorMaterial, backdropMaterial } from "./materials.js";

export class Room {
  constructor(scene) {
    this.floor = new Mesh(new PlaneGeometry(70, 16), floorMaterial());
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.position.set(0, 0, -1.5);
    this.floor.renderOrder = -1;
    this.backdrop = new Mesh(new PlaneGeometry(90, 30), backdropMaterial());
    this.backdrop.position.set(0, 15, -9.5);
    this.backdrop.renderOrder = -2;
    scene.add(this.floor, this.backdrop);
  }

  setTokens(t) {
    const f = this.floor.material.uniforms;
    f.uFloor.value.copy(t.floor);
    f.uFog.value.copy(t.fog);
    f.uPool.value.copy(t.pool);
    f.uRoomDim.value = t.roomDim;
    const b = this.backdrop.material.uniforms;
    b.uType.value = t.backdrop;
    b.uStars.value = t.stars;
    b.uBeamStrength.value = t.beamStrength;
    b.uTop.value.copy(t.skyTop);
    b.uBottom.value.copy(t.skyBottom);
    b.uFold.value.copy(t.fold);
    b.uFoldLight.value.copy(t.foldLight);
    b.uBeam.value.copy(t.beam);
    b.uRoomDim.value = t.roomDim;
  }

  setFog(near, far) {
    const f = this.floor.material.uniforms;
    f.uFogNear.value = near;
    f.uFogFar.value = far;
  }

  update(time, spotAt, level) {
    const f = this.floor.material.uniforms;
    f.uPoolAt.value.set(spotAt.x, spotAt.z + 0.3, level);
    const b = this.backdrop.material.uniforms;
    b.uTime.value = time;
    b.uSpotX.value = spotAt.x;
    b.uSpotLevel.value = level;
  }
}
