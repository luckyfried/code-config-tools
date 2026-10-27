// Model loading: the submarine glTF, with the primitive build as the fallback. Materials are tuned after load so the
// theme's hull color and the caustics reach the model whichever way it arrived.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { buildSubmarine } from "./submarine.js";
import { underwater } from "./materials.js";

export async function loadSubmarine(tokens, tier) {
  let root = null;
  try {
    const gltf = await withTimeout(new GLTFLoader().loadAsync("./models/submarine.glb"), 4000);
    root = gltf.scene.getObjectByName("submarine") || gltf.scene;
  } catch {
    root = buildSubmarine(THREE);
  }
  const props = [];
  const lamps = [];
  root.traverse((o) => {
    if (/Prop$/.test(o.name)) props.push(o);
    if (o.isMesh) {
      const m = o.material;
      if (m.name === "hull") m.color.copy(tokens.world.subHull);
      // The hull keeps its color in the dark: it reflects more of the water's light than the rock does.
      if (["hull", "trim"].includes(m.name)) m.envMapIntensity = 3.2;
      if (m.name === "hull") {
        m.emissive.copy(m.color);
        m.emissiveIntensity = 0.08;
      }
      if (m.name === "lamp") lamps.push(m);
      if (m.name === "glass") {
        m.transparent = true;
        m.depthWrite = false;
      }
      if (["hull", "trim", "frame", "duct"].includes(m.name) && !m.userData.underwater) {
        underwater(m, { caustics: tier.caustics, key: `sub-${m.name}`, rim: ["hull", "trim"].includes(m.name) });
        m.userData.underwater = true;
      }
    }
  });
  const sub = new THREE.Group();
  sub.name = "sub";
  sub.add(root);
  return {
    sub,
    spin(dt, thrust) {
      for (const p of props) p.rotation.z += dt * (4 + Math.abs(thrust) * 22);
    },
    setLamps(on) {
      for (const m of lamps) m.emissiveIntensity = on ? 5 : 0.2;
    },
  };
}

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))]);
}
