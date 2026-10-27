// Plants: instanced blades of grass and weed rooted in the sand, swaying in a vertex-shader current. Each theme
// grows its own kind: reef seagrass, tall river grass, and deep-sea whips with glowing tips.
import * as THREE from "three";
import { patchMaterial, shared } from "./shading.js";
import { sandHeight } from "./floor.js";
import { DEPTH_BACK } from "./world.js";

const STYLE = {
  reef: { height: [0.9, 2.6], width: 0.16, curl: 0.35, density: 1, glow: 0 },
  river: { height: [1.6, 5.2], width: 0.12, curl: 0.5, density: 1.2, glow: 0 },
  deep: { height: [1.0, 3.2], width: 0.07, curl: 0.25, density: 0.7, glow: 1.6 },
};

function bladeGeometry(segments, curl) {
  const pos = [], bend = [], col = [], idx = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const w = (1 - Math.pow(t, 1.6)) * 0.5 + 0.02;
    const z = curl * t * t;
    pos.push(-w, t, z, w, t, z);
    bend.push(t, t);
    col.push(t, t);
    if (i < segments) {
      const a = i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("aBend", new THREE.Float32BufferAttribute(bend, 1));
  g.setAttribute("aTip", new THREE.Float32BufferAttribute(col, 1));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export function createPlants(theme, pal, quality) {
  const style = STYLE[theme] || STYLE.reef;
  const group = new THREE.Group();
  const geo = bladeGeometry(7, style.curl);
  const material = new THREE.MeshStandardMaterial({ side: THREE.DoubleSide, roughness: 0.7, metalness: 0, envMapIntensity: 0.5 });
  const uTipGlow = { value: style.glow };
  const uRoot = { value: pal.plant.clone().multiplyScalar(0.45) };
  const uTip = { value: pal.plantTip.clone() };
  patchMaterial(material, { caustic: 0.9, sway: 0.42, key: `plant-${theme}` });
  const base = material.onBeforeCompile;
  material.onBeforeCompile = (shader) => {
    base(shader);
    Object.assign(shader.uniforms, { uTipGlow, uRoot, uTip, uNight: shared.uNight });
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute float aTip;\nvarying float vTip;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvTip = aTip;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uTipGlow, uNight;\nuniform vec3 uRoot, uTip;\nvarying float vTip;")
      .replace("vec4 diffuseColor = vec4( diffuse, opacity );", "vec4 diffuseColor = vec4( mix(uRoot, uTip, pow(clamp(vTip, 0.0, 1.0), 1.3)) * diffuse, opacity );")
      .replace("vec3 totalEmissiveRadiance = emissive;", "vec3 totalEmissiveRadiance = emissive + uTip * pow(clamp(vTip, 0.0, 1.0), 7.0) * uTipGlow * (0.5 + 0.8 * uNight);");
  };
  const max = Math.round((quality.phone ? 120 : 260) * style.density);
  const mesh = new THREE.InstancedMesh(geo, material, max);
  mesh.frustumCulled = false;
  group.add(mesh);

  function layout(frame) {
    let seed = 97;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const half = (frame.backRect.x1 - frame.backRect.x0) * 0.5;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const e = new THREE.Euler();
    const c = new THREE.Color();
    let n = 0;
    const put = (x, z, h) => {
      if (n >= max) return;
      const y = sandHeight(x, z) - 0.06;
      e.set(0, rnd() * Math.PI * 2, (rnd() - 0.5) * 0.25);
      q.setFromEuler(e);
      const w = style.width * (0.7 + rnd() * 0.7);
      m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(w / 0.5 * 0.5, h, w / 0.5 * 0.5));
      mesh.setMatrixAt(n, m);
      c.setScalar(0.75 + rnd() * 0.4);
      mesh.setColorAt(n, c);
      n++;
    };
    // a bed along the back glass, thicker at the corners
    const back = Math.round(max * 0.62);
    for (let i = 0; i < back; i++) {
      const x = (rnd() * 2 - 1) * half * 0.98;
      const corner = Math.abs(x) / half;
      const z = DEPTH_BACK + 0.1 + rnd() * (1.0 + corner * 1.6);
      const [h0, h1] = style.height;
      put(x, z, (h0 + (h1 - h0) * Math.pow(rnd(), 0.8)) * (0.75 + corner * 0.45));
    }
    // clumps at the front corners frame the view
    while (n < max) {
      const side = rnd() < 0.5 ? -1 : 1;
      const x = side * half * (0.55 + rnd() * 0.5);
      const z = 0.3 + rnd() * 2.0;
      const [h0, h1] = style.height;
      put(x, z, (h0 + (h1 - h0) * rnd()) * 0.7);
    }
    mesh.count = n;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }

  return { group, layout };
}
