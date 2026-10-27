// Live views in the shop: each species swims in its own card and each piece of decor turns slowly, drawn by one
// small renderer on a see-through canvas above the sheet, one scissored viewport per visible card.
import * as THREE from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { speciesMesh } from "./fish.js";
import { buildPiece } from "./decor.js";

export function createShowcase(canvas, catalog, dpr) {
  let renderer = null;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 50);
  scene.add(new THREE.HemisphereLight(0xeaf6ff, 0x2a3a44, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(2, 5, 4);
  scene.add(sun);
  const models = new Map();
  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler(0, 0, 0, "YXZ");

  function ensure() {
    if (renderer) return renderer;
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(dpr);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.setClearColor(0x000000, 0);
    new HDRLoader().loadAsync("vendor/env/soft-water.hdr").then((tex) => {
      const pmrem = new THREE.PMREMGenerator(renderer);
      scene.environment = pmrem.fromEquirectangular(tex).texture;
      tex.dispose();
      pmrem.dispose();
    }).catch(() => {});
    return renderer;
  }

  function modelFor(kind, id) {
    const key = `${kind}:${id}`;
    let m = models.get(key);
    if (m) return m;
    if (kind === "fish") {
      const spec = catalog.species.find((s) => s.id === id);
      const mesh = speciesMesh(spec, 1);
      mesh.count = 1;
      const length = 1 + spec.tail.size * 1.2;
      m = { kind, mesh, spec, radius: Math.max(length * 0.55, spec.body.height * 1.6 + (spec.dorsal?.height || 0)), phase: Math.random() * 6 };
    } else {
      const item = catalog.decor.find((d) => d.id === id);
      const mesh = buildPiece(item);
      const box = new THREE.Box3().setFromObject(mesh);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      mesh.position.sub(sphere.center);
      const holder = new THREE.Group();
      holder.add(mesh);
      m = { kind, mesh: holder, radius: sphere.radius };
    }
    m.mesh.visible = false;
    scene.add(m.mesh);
    models.set(key, m);
    return m;
  }

  function resize() {
    if (!renderer) return;
    renderer.setSize(window.innerWidth, window.innerHeight, false);
  }

  // views: [{ el, kind, id }]; clip: the rect views may draw inside
  function render(views, clip, time, dt) {
    ensure();
    const w = window.innerWidth, h = window.innerHeight;
    if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) resize();
    renderer.setScissorTest(false);
    renderer.clear();
    renderer.setScissorTest(true);
    for (const v of views) {
      const r = v.el.getBoundingClientRect();
      const x0 = Math.max(r.left, clip.left), x1 = Math.min(r.right, clip.right);
      const y0 = Math.max(r.top, clip.top), y1 = Math.min(r.bottom, clip.bottom);
      if (x1 - x0 < 2 || y1 - y0 < 2) continue;
      const m = modelFor(v.kind, v.id);
      for (const other of models.values()) other.mesh.visible = false;
      m.mesh.visible = true;
      camera.aspect = r.width / r.height;
      const fit = m.radius / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / Math.min(1, camera.aspect);
      camera.position.set(0, m.kind === "fish" ? 0.05 : m.radius * 0.35, fit * (m.kind === "fish" ? 1.02 : 1.1));
      camera.lookAt(0, 0, 0);
      camera.updateProjectionMatrix();
      if (m.kind === "fish") {
        m.phase += dt * Math.PI * 2 * m.spec.freq * 1.1;
        e.set(Math.sin(time * 0.7 + m.phase * 0.01) * 0.08, Math.PI / 2 + Math.sin(time * 0.45) * 0.45, 0);
        q.setFromEuler(e);
        m4.compose(new THREE.Vector3(0.12, Math.sin(time * 1.1) * 0.03, 0), q, new THREE.Vector3(1, 1, 1));
        m.mesh.setMatrixAt(0, m4);
        m.mesh.instanceMatrix.needsUpdate = true;
        const sw = m.mesh.geometry.attributes.iSwim;
        sw.array[0] = m.phase;
        sw.array[1] = Math.sin(time * 0.45 + 1.4) * 0.12;
        sw.array[2] = 0.3;
        sw.needsUpdate = true;
      } else {
        m.mesh.rotation.y = time * 0.4;
      }
      const bottom = h - r.bottom;
      renderer.setViewport(r.left, bottom, r.width, r.height);
      renderer.setScissor(x0, h - y1, x1 - x0, y1 - y0);
      renderer.render(scene, camera);
    }
  }

  function clear() {
    if (!renderer) return;
    renderer.setScissorTest(false);
    renderer.clear();
  }

  return { render, clear, resize };
}
