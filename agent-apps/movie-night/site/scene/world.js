// The 3D room assembled: renderer, camera rig, room, wall, and spotlight. step() moves things at the fixed rate;
// render() draws one frame.
import { Scene, Raycaster, Vector2, Vector3 } from "three";
import { createRenderer } from "./renderer.js";
import { Rig } from "./camera.js";
import { Room } from "./room.js";
import { Wall } from "./wall.js";
import { Spotlight } from "./spotlight.js";

export function createWorld({ canvas, tier, tokens }) {
  const renderer = createRenderer(canvas, tier);
  const scene = new Scene();
  const rig = new Rig();
  const room = new Room(scene);
  const wall = new Wall(scene, renderer);
  const light = new Spotlight(scene, tier.dust);
  const raycaster = new Raycaster();
  const ndc = new Vector2();
  const at = new Vector3();
  light.setPixel(tier.ratio);

  const setTokens = (t) => {
    room.setTokens(t);
    wall.setTokens(t);
    light.setTokens(t);
    renderer.setClearColor(t.floor);
  };
  setTokens(tokens);

  let phone = innerWidth < 900;
  const resize = () => {
    phone = innerWidth < 900;
    renderer.setSize(innerWidth, innerHeight, false);
    rig.resize(innerWidth, innerHeight, phone);
  };
  resize();

  return {
    renderer,
    setTokens,
    resize,
    setFilms: (films, sources) => wall.setFilms(films, sources),
    setSource: (i, source) => wall.setSource(i, source),
    setCover: (right, bottom, instant, floor) => rig.setCover(right, bottom, instant, floor),
    setRatio(r) {
      renderer.setPixelRatio(r);
      light.setPixel(r);
      resize();
    },
    step(dt, s) {
      rig.update(dt);
      wall.setFog(rig.dist + 0.8, rig.dist + 12);
      room.setFog(rig.dist + 1.5, rig.dist + 14);
      wall.update(dt, s.p, phone, s.spot, s.hover);
    },
    render(time, s) {
      if (!wall.worldOf(s.spot.index, at)) at.set(0, 0, 0);
      room.update(time, at, s.spot.level);
      light.update(time, at, s.spot.level, s.spot.drop);
      renderer.render(scene, rig.camera);
    },
    pick(x, y) {
      ndc.set((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1);
      raycaster.setFromCamera(ndc, rig.camera);
      const hit = raycaster.intersectObjects(wall.meshes(), false)[0];
      return hit ? hit.object.userData.index : -1;
    },
    dispose() {
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
