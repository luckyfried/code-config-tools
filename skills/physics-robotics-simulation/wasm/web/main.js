// The page: draws what the worker simulates, and sends it the person's controls.
// ?bundle=/bundle/ picks the served bundle; ?threads=1 asks for the multi-threaded build, which
// runs only when the page is cross-origin isolated (node serve.mjs BUNDLE --isolate).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

THREE.Object3D.DEFAULT_UP.set(0, 0, 1); // MuJoCo is +Z up
const params = new URLSearchParams(location.search);
const base = params.get('bundle') || '/bundle/';
const wantThreads = params.get('threads') === '1';
const threads = wantThreads && self.crossOriginIsolated;
const $ = (id) => document.getElementById(id);
const state = { ready: false, t: 0, steps: 0, ncon: 0, loads: 0, heapBytes: [], errors: [], threads };
window.__preview = state;
if (wantThreads && !threads) $('error').textContent = 'threads need a cross-origin isolated page (serve.mjs --isolate); running single-threaded';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
$('view').appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x15171c);
scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(1, -2, 3);
scene.add(sun);
const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
const orbit = new OrbitControls(camera, renderer.domElement);
function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();

const quat = (q) => new THREE.Quaternion(q[1], q[2], q[3], q[0]); // MuJoCo w,x,y,z
let bodies = [];
let root = null;

function geometryOf(g) {
  const [a, b, c] = g.size;
  switch (g.type) {
    case 0: return new THREE.PlaneGeometry(a > 0 ? 2 * a : 20, b > 0 ? 2 * b : 20);
    case 2: return new THREE.SphereGeometry(a, 32, 16);
    case 3: return new THREE.CapsuleGeometry(a, 2 * b, 8, 24).rotateX(Math.PI / 2);
    case 4: return new THREE.SphereGeometry(1, 32, 16).scale(a, b, c);
    case 5: return new THREE.CylinderGeometry(a, a, 2 * b, 32).rotateX(Math.PI / 2);
    case 6: return new THREE.BoxGeometry(2 * a, 2 * b, 2 * c);
    case 7: {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(g.vert, 3));
      geo.setIndex(new THREE.BufferAttribute(g.face, 1));
      geo.computeVertexNormals();
      return geo;
    }
    default: return null; // height fields are not drawn by this preview
  }
}

function disposeScene() {
  if (!root) return;
  root.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });
  scene.remove(root);
  root = null;
  bodies = [];
}

function build(msg) {
  disposeScene();
  root = new THREE.Group();
  bodies = Array.from({ length: msg.nbody }, () => root.add(new THREE.Group()) && root.children.at(-1));
  for (const g of msg.geoms) {
    const geo = geometryOf(g);
    if (!geo) continue;
    const [r, gr, b, alpha] = g.rgba;
    const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(r, gr, b), roughness: 0.6,
      transparent: alpha < 1, opacity: alpha, side: g.type === 0 ? THREE.DoubleSide : THREE.FrontSide });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.fromArray(g.pos);
    mesh.quaternion.copy(quat(g.quat));
    bodies[g.body].add(mesh);
  }
  scene.add(root);
  const [cx, cy, cz] = msg.stat.center;
  const e = msg.stat.extent;
  if (!state.loads) {
    orbit.target.set(cx, cy, cz);
    camera.position.set(cx + 0.4 * e, cy - 2.2 * e, cz + 0.9 * e);
    orbit.update();
  }
  const box = $('sliders');
  box.replaceChildren();
  msg.actuators.forEach((a, i) => {
    const label = document.createElement('label');
    const out = document.createElement('span');
    const input = Object.assign(document.createElement('input'), { type: 'range', min: a.range[0], max: a.range[1],
      step: (a.range[1] - a.range[0]) / 400 || 0.01, value: a.value, id: `ctrl${i}` });
    out.textContent = (+a.value).toFixed(2);
    input.oninput = () => { out.textContent = (+input.value).toFixed(2); worker.postMessage({ type: 'ctrl', index: i, value: +input.value }); };
    label.append(a.name, out, input);
    box.append(label);
  });
}

const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
let waiting = null;
worker.onmessage = ({ data: msg }) => {
  if (msg.type === 'ready') {
    build(msg);
    state.ready = true;
    state.loads += 1;
    state.version = msg.version;
    state.heapBytes.push(msg.heapBytes);
    waiting?.();
  } else if (msg.type === 'frame') {
    for (let b = 1; b < bodies.length; b++) {
      bodies[b].position.set(msg.xpos[3 * b], msg.xpos[3 * b + 1], msg.xpos[3 * b + 2]);
      bodies[b].quaternion.set(msg.xquat[4 * b + 1], msg.xquat[4 * b + 2], msg.xquat[4 * b + 3], msg.xquat[4 * b]);
    }
    Object.assign(state, { t: msg.t, steps: msg.steps, ncon: msg.ncon, running: msg.running });
    $('status').textContent = `mujoco ${state.version} ${threads ? 'threads' : 'single thread'}\n` +
      `t ${msg.t.toFixed(3)} s   steps ${msg.steps}   contacts ${msg.ncon}\nloads ${state.loads}`;
  } else if (msg.type === 'reset') {
    msg.ctrl.forEach((v, i) => { const s = $(`ctrl${i}`); if (s) { s.value = v; s.previousSibling.textContent = v.toFixed(2); } });
  } else if (msg.type === 'error') {
    state.errors.push(msg.message);
    $('error').textContent = msg.message;
    waiting?.();
  }
};

const load = () => new Promise((resolve) => { waiting = resolve; worker.postMessage({ type: 'load', base, threads }); });
$('play').onclick = () => {
  const playing = $('play').textContent === 'Pause';
  worker.postMessage({ type: playing ? 'pause' : 'play' });
  $('play').textContent = playing ? 'Play' : 'Pause';
};
$('reset').onclick = () => worker.postMessage({ type: 'reset' });
$('reload').onclick = async () => {
  for (let i = 0; i < 20; i++) await load();
};
addEventListener('pagehide', () => { worker.postMessage({ type: 'dispose' }); disposeScene(); renderer.dispose(); });

renderer.setAnimationLoop(() => renderer.render(scene, camera));
load();
