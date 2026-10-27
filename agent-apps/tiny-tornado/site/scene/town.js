// The town's meshes: one instanced mesh per prop kind, all sharing one material that colors each part from the
// theme's prop palette, lights the windows at night, and bends anything with flex (trees, fences) toward the funnel.
// The water tower carries the town's name. Planks are their own pool, colored per plank.
import * as THREE from "three";
import * as PROPS from "./props.js";
import { PALETTE, PAL } from "./tokens.js";

export const PLANKS = 320;

export function createPropMaterial(tokens) {
  const shared = {
    uPalette: { value: PALETTE.map(() => new THREE.Color()) },
    uFunnelP: { value: new THREE.Vector3() },
    uReach: { value: 2 },
    uTime: { value: 0 },
    uGlow: { value: 0 },
  };
  const material = new THREE.MeshStandardMaterial({ roughness: 0.82, metalness: 0.0, flatShading: true });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, shared);
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
        attribute float aPal;
        attribute float aFlex;
        attribute float aStand;
        uniform vec3 uPalette[${PALETTE.length}];
        uniform vec3 uFunnelP;
        uniform float uReach;
        uniform float uTime;
        varying vec3 vPal;
        varying float vWin;`,
      )
      .replace(
        "#include <color_vertex>",
        `#include <color_vertex>
        vPal = aPal < -0.5 ? vec3(1.0) : uPalette[int(aPal + 0.5)];
        vWin = abs(aPal - ${PAL.window.toFixed(1)}) < 0.5 ? 1.0 : 0.0;`,
      )
      .replace(
        "#include <project_vertex>",
        `vec4 ttWorld = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
        ttWorld = instanceMatrix * ttWorld;
        #endif
        ttWorld = modelMatrix * ttWorld;
        float ttFlex = aFlex * aStand;
        if (ttFlex > 0.0) {
          vec2 toF = uFunnelP.xz - ttWorld.xz;
          float d = length(toF);
          vec2 dirIn = toF / max(d, 0.001);
          float near = exp(-max(d - uReach * 0.5, 0.0) / (uReach * 1.7));
          float ripple = sin(uTime * 1.4 + ttWorld.x * 0.13 + ttWorld.z * 0.1) * 0.1 + sin(uTime * 9.0 + ttWorld.x * 1.3 + ttWorld.z) * 0.22 * near;
          vec2 off = (dirIn * near * 1.7 + vec2(-dirIn.y, dirIn.x) * near * 0.9 + vec2(ripple, ripple * 0.6)) * ttFlex;
          ttWorld.xz += off;
          ttWorld.y -= dot(off, off) * 0.12;
        }
        vec4 mvPosition = viewMatrix * ttWorld;
        gl_Position = projectionMatrix * mvPosition;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uGlow;
        varying vec3 vPal;
        varying float vWin;`,
      )
      .replace("#include <color_fragment>", `#include <color_fragment>
        diffuseColor.rgb *= vPal;`)
      .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>
        totalEmissiveRadiance += vPal * vWin * uGlow;`);
  };
  material.customProgramCacheKey = () => "tt-prop";
  const api = {
    material,
    shared,
    applyTokens(t) {
      PALETTE.forEach((name, i) => shared.uPalette.value[i].copy(t.colors[name.replace(/-([a-z])/g, (_, c) => c.toUpperCase())]));
      shared.uGlow.value = t.numbers.propWindowGlow;
    },
  };
  api.applyTokens(tokens);
  return api;
}

const BUILDERS = {
  fence: PROPS.fence,
  hay: PROPS.hay,
  treeRound: PROPS.treeRound,
  treePine: PROPS.treePine,
  cow: PROPS.cow,
  car: PROPS.car,
  truck: PROPS.truck,
  barn: PROPS.barn,
  silo: PROPS.silo,
  house: PROPS.house,
  houseB: PROPS.houseB,
};

export function createTownMeshes({ town, propMaterial, shadows }) {
  const group = new THREE.Group();
  const meshes = {};
  const geometries = {};
  const counts = {};
  for (const p of town.props) counts[p.type] = (counts[p.type] || 0) + 1;
  for (const type of Object.keys(BUILDERS)) {
    const n = counts[type] || 0;
    if (!n) continue;
    const geometry = BUILDERS[type]();
    geometries[type] = geometry;
    const instanced = geometry.clone();
    instanced.setAttribute("aStand", new THREE.InstancedBufferAttribute(new Float32Array(n).fill(1), 1));
    const mesh = new THREE.InstancedMesh(instanced, propMaterial.material, n);
    mesh.castShadow = shadows;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    meshes[type] = mesh;
    group.add(mesh);
  }

  const plankGeometry = PROPS.plank();
  plankGeometry.getAttribute("aPal").array.fill(-1);
  plankGeometry.setAttribute("aStand", new THREE.InstancedBufferAttribute(new Float32Array(PLANKS), 1));
  const planks = new THREE.InstancedMesh(plankGeometry, propMaterial.material, PLANKS);
  planks.castShadow = shadows;
  planks.frustumCulled = false;
  planks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  const white = new THREE.Color(1, 1, 1);
  for (let i = 0; i < PLANKS; i++) {
    planks.setMatrixAt(i, zero);
    planks.setColorAt(i, white);
  }
  group.add(planks);

  return { group, meshes, geometries, planks };
}

// The water tower: four legs with braces, a tank painted with the town's name twice around, and a pointed cap.
export function createWaterTower({ town, name, tokens, shadows }) {
  const group = new THREE.Group();
  group.position.set(town.tower.x, 0, town.tower.z);
  const canvas = document.createElement("canvas");
  canvas.width = 2048;
  canvas.height = 384;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  const tankMaterial = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.5, metalness: 0.15 });
  const metal = new THREE.MeshStandardMaterial({ roughness: 0.6, metalness: 0.2 });
  const legH = 13;
  for (const [x, z] of [[-2.4, -2.4], [2.4, -2.4], [-2.4, 2.4], [2.4, 2.4]]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.26, legH, 8), metal);
    leg.position.set(x * 0.9, legH / 2, z * 0.9);
    leg.rotation.set(z * 0.012, 0, -x * 0.012);
    group.add(leg);
  }
  for (const y of [4.5, 9]) {
    for (const [ax, az, rot] of [[0, -2.2, 0], [0, 2.2, 0], [-2.2, 0, Math.PI / 2], [2.2, 0, Math.PI / 2]]) {
      const brace = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.14, 0.14), metal);
      brace.position.set(ax, y, az);
      brace.rotation.y = rot;
      group.add(brace);
    }
  }
  const tank = new THREE.Mesh(new THREE.CylinderGeometry(3.4, 3.4, 4.8, 48, 1, false, -Math.PI / 2, Math.PI * 2), [
    tankMaterial, metal, metal,
  ]);
  tank.position.y = legH + 2.4;
  group.add(tank);
  const cap = new THREE.Mesh(new THREE.ConeGeometry(3.6, 2.2, 48), metal);
  cap.position.y = legH + 4.8 + 1.1;
  group.add(cap);
  const rim = new THREE.Mesh(new THREE.CylinderGeometry(3.55, 3.55, 0.3, 48), metal);
  rim.position.y = legH;
  group.add(rim);
  group.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = shadows;
      o.receiveShadow = true;
    }
  });

  function paint(t) {
    const g = canvas.getContext("2d");
    g.fillStyle = t.hex.towerPaint;
    g.fillRect(0, 0, canvas.width, canvas.height);
    g.fillStyle = t.hex.towerInk;
    g.fillRect(0, 22, canvas.width, 14);
    g.fillRect(0, canvas.height - 36, canvas.width, 14);
    const text = name.toUpperCase();
    let size = 200;
    g.font = `800 ${size}px "Bricolage Grotesque", system-ui, sans-serif`;
    const widest = canvas.width * 0.3;
    const w = g.measureText(text).width;
    if (w > widest) size = Math.max(70, Math.floor((size * widest) / w));
    g.font = `800 ${size}px "Bricolage Grotesque", system-ui, sans-serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    for (const u of [0.25, 0.75]) g.fillText(text, canvas.width * u, canvas.height / 2 + size * 0.04);
    texture.needsUpdate = true;
    metal.color.copy(t.colors.towerPaint).multiplyScalar(0.92);
  }
  paint(tokens);
  return { group, applyTokens: paint };
}
