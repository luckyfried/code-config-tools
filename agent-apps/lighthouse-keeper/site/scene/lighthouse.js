// The lighthouse on its reef: a banded tower with the keeper's name painted around it, a gallery, the lamp room,
// lit windows, the keeper's cottage, and the rocks that wreck the ships.
import * as THREE from "three";
import { ImprovedNoise } from "three/addons/math/ImprovedNoise.js";
import { merge, paint } from "./geometry.js";

export const LAMP_HEIGHT = 15.6;
export const REEF_RADIUS = 12.5;

function nameTexture(name, tokens) {
  const canvas = document.createElement("canvas");
  canvas.width = 2048;
  canvas.height = 128;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  const draw = () => {
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = tokens.cssTower || "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = tokens.cssTrim || "black";
    ctx.font = '600 78px "Fraunces", Georgia, serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const label = name.toUpperCase();
    let size = 78;
    while (ctx.measureText(label).width > canvas.width * 0.26 && size > 30) {
      size -= 4;
      ctx.font = `600 ${size}px "Fraunces", Georgia, serif`;
    }
    for (const x of [canvas.width / 4, (canvas.width * 3) / 4]) ctx.fillText(label, x, canvas.height / 2 + 4);
    texture.needsUpdate = true;
  };
  draw();
  if (document.fonts) document.fonts.load('600 78px "Fraunces"').then(draw, () => {});
  return texture;
}

function rock(radius, detail, seed, squash) {
  const g = new THREE.IcosahedronGeometry(radius, detail);
  const noise = new ImprovedNoise();
  const p = g.attributes.position;
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const n = noise.noise(v.x * 0.45 + seed, v.y * 0.45, v.z * 0.45 - seed);
    v.multiplyScalar(1 + n * 0.5);
    v.y *= squash;
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

export function createLighthouse(tokens, name, tier) {
  const group = new THREE.Group();
  const white = tokens.tower;
  const band = tokens.towerBand;
  const trim = tokens.towerTrim;

  // Tower: three white and two colored bands, tapering from the base to the gallery.
  const towerParts = [];
  const bands = [white, band, white, band, white];
  const h0 = 2.2;
  const towerTop = 13.2;
  const step = (towerTop - h0) / bands.length;
  const radiusAt = (y) => 2.35 - ((y - h0) / (towerTop - h0)) * 0.85;
  bands.forEach((c, i) => {
    const y0 = h0 + i * step;
    const g = new THREE.CylinderGeometry(radiusAt(y0 + step), radiusAt(y0), step, 40, 1, true);
    g.translate(0, y0 + step / 2, 0);
    towerParts.push(paint(g, c));
  });
  const plinth = new THREE.CylinderGeometry(2.9, 3.3, 1.4, 40);
  plinth.translate(0, h0 - 0.7, 0);
  towerParts.push(paint(plinth, trim));
  const gallery = new THREE.CylinderGeometry(2.25, 1.75, 0.45, 40);
  gallery.translate(0, towerTop + 0.2, 0);
  towerParts.push(paint(gallery, trim));
  const rail = new THREE.TorusGeometry(2.15, 0.06, 6, 48);
  rail.rotateX(Math.PI / 2);
  rail.translate(0, towerTop + 1.0, 0);
  towerParts.push(paint(rail, trim));
  const roomBase = new THREE.CylinderGeometry(1.35, 1.4, 0.7, 24);
  roomBase.translate(0, towerTop + 0.75, 0);
  towerParts.push(paint(roomBase, trim));
  const roof = new THREE.ConeGeometry(1.6, 1.5, 24);
  roof.translate(0, LAMP_HEIGHT + 1.45, 0);
  towerParts.push(paint(roof, trim));
  const finial = new THREE.SphereGeometry(0.22, 10, 8);
  finial.translate(0, LAMP_HEIGHT + 2.3, 0);
  towerParts.push(paint(finial, trim));
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const mullion = new THREE.BoxGeometry(0.09, 1.5, 0.09);
    mullion.translate(Math.cos(a) * 1.28, LAMP_HEIGHT - 0.05, Math.sin(a) * 1.28);
    towerParts.push(paint(mullion, trim));
  }

  // The keeper's cottage beside the tower.
  const cottage = new THREE.BoxGeometry(4.2, 2.4, 3.2);
  cottage.translate(4.2, 1.9, 1.6);
  towerParts.push(paint(cottage, white));
  const cottageRoof = new THREE.CylinderGeometry(0.01, 2.6, 1.6, 4, 1);
  cottageRoof.rotateY(Math.PI / 4);
  cottageRoof.scale(1.15, 1, 0.9);
  cottageRoof.translate(4.2, 3.9, 1.6);
  towerParts.push(paint(cottageRoof, trim));

  const towerMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.78, metalness: 0 });
  nightGlow(towerMat, tokens);
  const tower = new THREE.Mesh(merge(towerParts), towerMat);
  tower.castShadow = tier.shadow > 0;
  tower.receiveShadow = tier.shadow > 0;
  group.add(tower);

  // The name, painted on a ring around the middle white band.
  const yName = h0 + step * 2.5;
  const nameRing = new THREE.CylinderGeometry(radiusAt(yName + 0.7) + 0.012, radiusAt(yName - 0.7) + 0.012, 1.4, 64, 1, true);
  nameRing.translate(0, yName, 0);
  const nameMat = new THREE.MeshStandardMaterial({ map: nameTexture(name, tokens), roughness: 0.8 });
  nightGlow(nameMat, tokens);
  const nameMesh = new THREE.Mesh(nameRing, nameMat);
  nameMesh.rotation.y = Math.PI * 0.5;
  group.add(nameMesh);

  // Lit windows up the tower and in the cottage.
  const windows = [];
  for (const [y, a] of [[4.6, 0.35], [7.4, -0.5], [10.2, 0.2], [12.1, -0.2]]) {
    const r = radiusAt(y) + 0.02;
    const w = new THREE.PlaneGeometry(0.42, 0.7);
    w.translate(0, 0, r);
    w.rotateY(a + Math.PI);
    w.translate(0, y, 0);
    windows.push(w);
  }
  for (const x of [3.3, 5.1]) {
    const w = new THREE.PlaneGeometry(0.6, 0.7);
    w.translate(x, 2.0, 3.21);
    windows.push(w);
  }
  const windowMat = new THREE.MeshBasicMaterial({ color: tokens.window.clone().multiplyScalar(2.2), side: THREE.DoubleSide });
  group.add(new THREE.Mesh(merge(windows), windowMat));

  // The lamp: a bright core and a lens that turns with the beam.
  const lampMat = new THREE.MeshBasicMaterial({ color: tokens.lamp.clone().multiplyScalar(6), depthWrite: false });
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 12), lampMat);
  lamp.position.y = LAMP_HEIGHT;
  group.add(lamp);
  const lens = new THREE.Mesh(
    new THREE.CylinderGeometry(0.95, 0.95, 1.2, 12, 1, true),
    new THREE.MeshBasicMaterial({ color: tokens.lamp.clone().multiplyScalar(1.6), transparent: true, opacity: 0.35, depthWrite: false, blending: THREE.AdditiveBlending }),
  );
  lens.position.y = LAMP_HEIGHT;
  group.add(lens);

  // The reef: one big rock under the tower and a ring of smaller rocks that wreck the ships.
  const rockParts = [];
  const base = rock(6.5, 3, 1.3, 0.42);
  base.translate(0, -0.4, 0);
  rockParts.push(base);
  const reef = [];
  let seed = 3;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 15; i++) {
    const a = (i / 15) * Math.PI * 2 + rand() * 0.3;
    const d = 8.5 + rand() * 5;
    const r = 0.9 + rand() * 1.7;
    const g = rock(r, 1, i * 2.7, 0.75);
    const x = Math.cos(a) * d;
    const z = Math.sin(a) * d;
    g.translate(x, -0.25 + r * 0.15, z);
    rockParts.push(g);
    reef.push(new THREE.Vector3(x, r * 0.7, z));
  }
  const rockMat = new THREE.MeshStandardMaterial({ color: tokens.rock, roughness: 0.95, flatShading: true });
  const rocks = new THREE.Mesh(merge(rockParts), rockMat);
  rocks.castShadow = tier.shadow > 0;
  rocks.receiveShadow = tier.shadow > 0;
  group.add(rocks);

  return {
    group,
    lamp,
    lens,
    reef,
    lampPosition: new THREE.Vector3(0, LAMP_HEIGHT, 0),
    setBearing(b) {
      lens.rotation.y = -b;
    },
    // Turns the painted name so one copy of it is centered on the side of the tower the camera sees.
    faceName(cameraPosition) {
      nameMesh.rotation.y = Math.PI * 0.5 + Math.atan2(cameraPosition.x, cameraPosition.z);
    },
  };
}

// The tower at night: spill from the lamp washes down from the gallery, the cottage windows warm its foot, and the
// moon catches its edges, so the bands and the name read in the dark. The light look keeps a trace of the same.
function nightGlow(material, tokens) {
  const strength = tokens.dark ? 1 : 0.3;
  const lamp = tokens.lamp.clone();
  const rim = tokens.moon.clone();
  const warm = tokens.window.clone();
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uLampSpill = { value: lamp };
    shader.uniforms.uMoonRim = { value: rim };
    shader.uniforms.uWarm = { value: warm };
    shader.uniforms.uNight = { value: strength };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vLkHeight;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvLkHeight = (modelMatrix * vec4(position, 1.0)).y;");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 uLampSpill, uMoonRim, uWarm;\nuniform float uNight;\nvarying float vLkHeight;",
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        float lkSpill = 0.1 + 0.55 * smoothstep(2.0, 14.5, vLkHeight) + 0.25 * (1.0 - smoothstep(1.0, 5.0, vLkHeight));
        vec3 lkTint = mix(uLampSpill, uWarm, 1.0 - smoothstep(1.0, 6.0, vLkHeight));
        float lkRim = pow(1.0 - abs(dot(normalize(vNormal), normalize(vViewPosition))), 3.0);
        totalEmissiveRadiance += uNight * (diffuseColor.rgb * lkTint * lkSpill * 0.55 + uMoonRim * lkRim * 0.35);`,
      );
  };
}
