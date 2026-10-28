// Small objects that style the shelf: a snake plant, a glazed vase with dried stems, a candle, a framed print,
// river stones, brass bookends, and the walnut easels that hold the books being read face-out.
import * as THREE from "three";
import { brass, glaze, matte } from "./materials.js";
import { printCanvas, glowCanvas, rng, hash } from "./textures.js";
import { canvasTexture } from "./renderer.js";

function lathe(points, segments = 28) {
  return new THREE.LatheGeometry(points.map(([x, y]) => new THREE.Vector2(x, y)), segments);
}

function shadowed(mesh) {
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function bladeTexture(renderer) {
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 256;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#2f5a34";
  ctx.fillRect(0, 0, 64, 256);
  for (let y = 0; y < 256; y += 14) {
    ctx.fillStyle = "rgba(170,200,120,0.28)";
    ctx.beginPath();
    ctx.ellipse(32, y, 26, 4, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = "#c9b75a";
  ctx.fillRect(0, 0, 5, 256);
  ctx.fillRect(59, 0, 5, 256);
  return canvasTexture(c, renderer);
}

export function createDecorKit(renderer, tokens) {
  const kit = {
    brass: brass(),
    walnut: matte("#4a2f1d", 0.55),
    soil: matte("#2a1d14", 1),
    candle: matte("#efe6d2", 0.6),
    pot: glaze(tokens.books[4]),
    vase: glaze(tokens.books[0]),
    stone: [matte("#8d8a83", 0.7), matte("#5d5a55", 0.6), matte("#b5afa4", 0.75)],
    leaf: new THREE.MeshStandardMaterial({ map: bladeTexture(renderer), roughness: 0.55, side: THREE.DoubleSide }),
    stem: matte("#6b5a44", 0.9),
    seed: matte("#a89b78", 0.8),
    glowTex: canvasTexture(glowCanvas(), renderer),
    flames: [],
    printTex: null,
  };
  kit.printTex = canvasTexture(printCanvas(tokens, 5), renderer);
  return kit;
}

export function recolorDecor(kit, tokens) {
  kit.pot.color.set(tokens.books[4]);
  kit.vase.color.set(tokens.books[0]);
}

function plant(kit, scale) {
  const g = new THREE.Group();
  const pot = shadowed(new THREE.Mesh(lathe([[0, 0], [0.04, 0], [0.046, 0.006], [0.05, 0.07], [0.054, 0.074], [0.054, 0.08], [0.048, 0.08], [0.046, 0.074], [0, 0.072]]), kit.pot));
  g.add(pot);
  const soil = new THREE.Mesh(new THREE.CircleGeometry(0.046, 24), kit.soil);
  soil.rotation.x = -Math.PI / 2;
  soil.position.y = 0.074;
  g.add(soil);
  const r = rng(11);
  for (let i = 0; i < 9; i += 1) {
    const h = 0.11 + r() * 0.1;
    const geo = new THREE.PlaneGeometry(0.022, h, 1, 6);
    const p = geo.attributes.position;
    for (let j = 0; j < p.count; j += 1) {
      const yy = (p.getY(j) + h / 2) / h;
      p.setX(j, p.getX(j) * (1 - yy * 0.85));
      p.setZ(j, yy * yy * 0.03);
    }
    geo.translate(0, h / 2, 0);
    geo.computeVertexNormals();
    const blade = shadowed(new THREE.Mesh(geo, kit.leaf));
    const a = (i / 9) * Math.PI * 2 + r() * 0.4;
    blade.position.set(Math.cos(a) * 0.014, 0.07, Math.sin(a) * 0.014);
    blade.rotation.set(0, -a + Math.PI / 2, 0);
    blade.rotateX(-0.12 - r() * 0.22);
    g.add(blade);
  }
  g.scale.setScalar(scale);
  return g;
}

function vase(kit, scale) {
  const g = new THREE.Group();
  const body = shadowed(
    new THREE.Mesh(lathe([[0, 0], [0.03, 0], [0.042, 0.02], [0.046, 0.06], [0.036, 0.11], [0.016, 0.14], [0.014, 0.16], [0.018, 0.168], [0.012, 0.168], [0, 0.15]]), kit.vase),
  );
  g.add(body);
  const r = rng(23);
  for (let i = 0; i < 3; i += 1) {
    const lean = (i - 1) * 0.08 + (r() - 0.5) * 0.04;
    const pts = [new THREE.Vector3(0, 0.12, 0), new THREE.Vector3(lean * 0.6, 0.2, 0.01), new THREE.Vector3(lean * 1.4, 0.27 + r() * 0.04, 0.02 * (r() - 0.5))];
    const curve = new THREE.CatmullRomCurve3(pts);
    g.add(shadowed(new THREE.Mesh(new THREE.TubeGeometry(curve, 10, 0.0015, 4), kit.stem)));
    for (let k = 0; k < 7; k += 1) {
      const q = curve.getPoint(0.45 + k * 0.08);
      const s = new THREE.Mesh(new THREE.SphereGeometry(0.006 + r() * 0.003, 8, 6), kit.seed);
      s.position.copy(q).add(new THREE.Vector3((r() - 0.5) * 0.012, 0, (r() - 0.5) * 0.008));
      s.scale.set(1, 0.6, 1);
      s.castShadow = true;
      g.add(s);
    }
  }
  g.scale.setScalar(scale);
  return g;
}

function candle(kit, scale, lit) {
  const g = new THREE.Group();
  g.add(shadowed(new THREE.Mesh(lathe([[0, 0], [0.045, 0], [0.05, 0.008], [0.046, 0.012], [0.018, 0.012], [0.016, 0.03], [0, 0.03]]), kit.brass)));
  const wax = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.015, 0.11, 18), kit.candle));
  wax.position.y = 0.03 + 0.055;
  g.add(wax);
  const wick = new THREE.Mesh(new THREE.CylinderGeometry(0.0009, 0.0009, 0.008, 4), kit.soil);
  wick.position.y = 0.144;
  g.add(wick);
  const flame = new THREE.Sprite(new THREE.SpriteMaterial({ map: kit.glowTex, color: "#ffc77a", blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  flame.position.y = 0.16;
  flame.scale.set(0.018, 0.034, 1);
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: kit.glowTex, color: "#ff9a3c", blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.35 }));
  halo.position.y = 0.155;
  halo.scale.set(0.12, 0.12, 1);
  g.add(flame, halo);
  kit.flames.push({ flame, halo, seed: Math.random() * 10 });
  flame.visible = lit;
  halo.visible = lit;
  g.scale.setScalar(scale);
  return g;
}

function frame(kit, scale) {
  const g = new THREE.Group();
  const w = 0.12;
  const h = 0.155;
  const border = shadowed(new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.012), kit.walnut));
  border.position.y = h / 2;
  g.add(border);
  const mat = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.02, h - 0.02), new THREE.MeshStandardMaterial({ map: kit.printTex, roughness: 0.7 }));
  mat.position.set(0, h / 2, 0.0065);
  g.add(mat);
  g.rotation.x = -0.16;
  g.position.z = -0.07;
  g.scale.setScalar(scale);
  return g;
}

function stones(kit, scale) {
  const g = new THREE.Group();
  const sizes = [
    [0.042, 0.016],
    [0.032, 0.014],
    [0.022, 0.012],
  ];
  let y = 0;
  sizes.forEach(([r, h], i) => {
    const s = shadowed(new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), kit.stone[i]));
    s.scale.set(r, h, r * 0.85);
    s.position.y = y + h;
    s.rotation.y = i * 0.7;
    y += h * 1.75;
    g.add(s);
  });
  g.scale.setScalar(scale);
  return g;
}

function bookend(kit, dir) {
  const g = new THREE.Group();
  const plate = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.004, 0.13, 0.1), kit.brass));
  plate.position.set(0.002 * dir, 0.065, -0.05);
  const foot = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.003, 0.1), kit.brass));
  foot.position.set(0.032 * dir, 0.0015, -0.05);
  g.add(plate, foot);
  return g;
}

function easel(kit, width, t, tilt = 0.2) {
  const g = new THREE.Group();
  const base = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width * 0.92, 0.012, t + 0.1), kit.walnut));
  base.position.set(0, 0.006, -0.035);
  const lip = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width * 0.92, 0.022, 0.008), kit.walnut));
  lip.position.set(0, 0.017, t / 2 + 0.008);
  // The back rest lies against the book's back cover at the book's own lean.
  const back = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.15, 0.008), kit.walnut));
  const rise = 0.07;
  back.position.set(0, 0.012 + rise * Math.cos(tilt), -t / 2 - 0.006 - rise * Math.sin(tilt));
  back.rotation.x = -tilt;
  g.add(base, lip, back);
  return g;
}

/** Builds the decor list from a layout into one group. */
export function buildDecor(kit, decor, front, lit) {
  kit.flames.length = 0;
  const group = new THREE.Group();
  for (const d of decor) {
    let obj = null;
    const fit = d.room ? Math.min(1, d.room / 0.14) : 1;
    if (d.type === "plant") obj = plant(kit, 0.95 * fit);
    else if (d.type === "vase") obj = vase(kit, 1.05 * fit);
    else if (d.type === "candle") obj = candle(kit, 1.1 * fit, lit);
    else if (d.type === "frame") obj = frame(kit, 1.15 * fit);
    else if (d.type === "stones") obj = stones(kit, d.small ? 0.8 : 1.2 * fit);
    else if (d.type === "bookend") obj = bookend(kit, d.dir);
    else if (d.type === "easel") obj = easel(kit, d.w, d.t, d.tilt);
    if (!obj) continue;
    const z = d.z !== undefined ? d.z : d.type === "bookend" ? front : front - 0.12;
    obj.position.x += d.x;
    obj.position.y += d.y;
    obj.position.z += z;
    if (d.type !== "easel" && d.type !== "bookend") obj.rotation.y += (rng(hash(`${d.seg}${d.type}`))() - 0.5) * 0.6;
    group.add(obj);
  }
  return group;
}

export function tickDecor(kit, time, lit) {
  for (const f of kit.flames) {
    f.flame.visible = lit;
    f.halo.visible = lit;
    if (!lit) continue;
    const n = Math.sin(time * 11 + f.seed) * 0.5 + Math.sin(time * 17.3 + f.seed * 2) * 0.3 + Math.sin(time * 5.1) * 0.2;
    f.flame.scale.set(0.017 + n * 0.0015, 0.034 + n * 0.004, 1);
    f.halo.material.opacity = 0.3 + n * 0.06;
  }
}
