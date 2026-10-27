// The 3D table: renderer, studio light, the room behind the board, the camera that sits behind the side to move, and
// the pieces on their squares. main.js drives it through setPosition, play, setHints, setCheck, mate, and setView.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { Board, SIZE, squareXZ, xzSquare, ONLY_MAIN } from "./board.js";
import { Piece, glassMaterials, marbleMaterials, renderIcons } from "./pieces.js";
import { Dust } from "./fx.js";
import { Tweens, fly, sink, tip, ease } from "./moves.js";
import { readTokens } from "./tokens.js";

const ROOM_VERTEX = /* glsl */`
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const ROOM_FRAGMENT = /* glsl */`
  uniform vec3 uTop;
  uniform vec3 uBottom;
  uniform vec3 uGlow;
  uniform float uGlowStrength;
  varying vec3 vDir;
  void main() {
    float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 c = mix(uBottom, uTop, smoothstep(0.35, 0.95, h));
    float glow = exp(-pow(length(vDir.xz) * 1.1 - 0.15, 2.0) * 2.0) * smoothstep(0.2, 0.55, h) * (1.0 - smoothstep(0.55, 0.9, h));
    c += uGlow * glow * uGlowStrength;
    gl_FragColor = vec4(c, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export function detectTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  const small = Math.min(innerWidth, innerHeight) < 700;
  return coarse || small ? "phone" : "desktop";
}

export class World {
  constructor(canvas, { tier, reduced }) {
    this.canvas = canvas;
    this.tier = tier;
    this.reduced = reduced;
    this.tweens = new Tweens();
    this.pieces = new Map();
    this.now = 0;
    this.listeners = new Set();
    this.view = { azimuth: 0, elevation: tier === "phone" ? 0.98 : 0.86, drag: 0, dragElevation: 0, drift: 0 };
    this.stage = { x: 0, y: 0, w: innerWidth, h: innerHeight };
    this.exposure = { value: 1, target: 1 };
    this.checkSquare = null;
    this.frameTimes = [];
    this.material = "glass";
  }

  async init() {
    const renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    // The mirror clears to nothing, so only the pieces show in the board's reflection.
    renderer.setClearAlpha(0);
    renderer.toneMapping = THREE.NeutralToneMapping;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.transmissionResolutionScale = this.tier === "phone" ? 0.6 : 1;
    this.renderer = renderer;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.5, 240);
    this.camera.layers.enable(ONLY_MAIN);

    const pmrem = new THREE.PMREMGenerator(renderer);
    this.environment = pmrem.fromScene(new RoomEnvironment(), 0.035).texture;
    pmrem.dispose();
    this.scene.environment = this.environment;

    this.room = new THREE.Mesh(
      new THREE.SphereGeometry(40, 32, 16),
      new THREE.ShaderMaterial({
        side: THREE.BackSide, depthWrite: false,
        uniforms: { uTop: { value: new THREE.Color() }, uBottom: { value: new THREE.Color() }, uGlow: { value: new THREE.Color() }, uGlowStrength: { value: 1 } },
        vertexShader: ROOM_VERTEX, fragmentShader: ROOM_FRAGMENT,
      }),
    );
    this.room.layers.set(ONLY_MAIN);
    this.scene.add(this.room);

    this.key = new THREE.DirectionalLight(0xffffff, 1);
    this.key.position.set(-5, 9, 4);
    this.scene.add(this.key);
    this.rim = new THREE.DirectionalLight(0xffffff, 1);
    this.rim.position.set(6, 4, -7);
    this.scene.add(this.rim);

    this.dust = new Dust(new THREE.Color(1, 1, 1), ONLY_MAIN);
    this.scene.add(this.dust.group);
    this.applyTheme();

    this.resize();
    addEventListener("resize", () => this.resize());
    await renderer.compileAsync(this.scene, this.camera);
    this.renderer.setAnimationLoop((t) => this.frame(t));
  }

  // Reads the theme's tokens and rebuilds everything that carries color: the board, the glass, the room, the light.
  applyTheme() {
    const tokens = readTokens();
    this.tokens = tokens;
    if (this.board) {
      this.scene.remove(this.board.group);
      this.board.group.traverse((o) => { o.geometry?.dispose(); o.material?.map?.dispose(); o.material?.dispose?.(); });
      this.board.mirror.dispose();
    }
    this.board = new Board({ tokens, tier: this.tier, renderer: this.renderer });
    this.scene.add(this.board.group);
    this.hookMirror();

    this.glass = glassMaterials(tokens, this.tier);
    this.marble = null;
    this.materials = this.material === "marble" ? (this.marble = marbleMaterials(tokens)) : this.glass;
    for (const p of this.pieces.values()) p.setMaterials(this.materials);

    const u = this.room.material.uniforms;
    u.uTop.value.copy(tokens.color("--room-top"));
    u.uBottom.value.copy(tokens.color("--room-bottom"));
    u.uGlow.value.copy(tokens.color("--room-glow"));
    u.uGlowStrength.value = tokens.number("--room-glow-strength", 0.4);
    this.scene.environmentIntensity = tokens.number("--env-intensity", 1);
    this.key.color.copy(tokens.color("--key-light"));
    this.key.intensity = tokens.number("--key-light-intensity", 1.2);
    this.rim.color.copy(tokens.color("--rim-light"));
    this.rim.intensity = tokens.number("--rim-light-intensity", 1);
    this.dust.setColor(tokens.color("--dust"));
    this.hintColors = {
      selected: tokens.color("--hint-selected"),
      target: tokens.color("--hint-target"),
      last: tokens.color("--hint-last"),
      cursor: tokens.color("--hint-cursor"),
    };
    this.icons = renderIcons(this.renderer, this.glass, this.environment, tokens);
    if (this.hintState) this.setHints(this.hintState);
    this.emit("theme");
  }

  // The mirror draws the scene a second time; there each piece wears its cheap stand-in instead of glass.
  hookMirror() {
    const mirror = this.board.mirror;
    const draw = mirror.onBeforeRender;
    const saved = [];
    mirror.onBeforeRender = (renderer, scene, camera) => {
      saved.length = 0;
      for (const p of this.pieces.values()) { saved.push(p, p.mesh.material); p.mesh.material = p.mirrorMaterial; }
      for (const p of this.leaving ?? []) { saved.push(p, p.mesh.material); p.mesh.material = p.mirrorMaterial; }
      draw.call(mirror, renderer, scene, camera);
      for (let i = 0; i < saved.length; i += 2) saved[i].mesh.material = saved[i + 1];
    };
  }

  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  emit(kind, data) { for (const fn of this.listeners) fn(kind, data); }

  // The part of the window the board should fill; the panels cover the rest. With `animate` the camera eases from
  // the old framing to the new one.
  setStage(rect, { animate = false } = {}) {
    this.stage = rect;
    if (!animate || this.reduced || !this.shift) { this.fit(); return; }
    const from = { d: this.distance, x: this.shift.x, y: this.shift.y };
    this.fit();
    const to = { d: this.distance, x: this.shift.x, y: this.shift.y };
    this.tweens.add(0.8, (t) => {
      const k = ease.inOut(t);
      this.distance = from.d + (to.d - from.d) * k;
      this.shift = { x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k };
    });
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.fit();
  }

  // Finds the camera distance that fits the board and its tallest pieces into the stage, then shifts the projection so
  // the board sits in the middle of the stage rather than the middle of the window.
  fit() {
    const cam = this.camera;
    const w = innerWidth, h = innerHeight;
    const s = this.stage;
    const sx = s.w / w, sy = s.h / h;
    const half = SIZE / 2;
    const pts = [];
    for (const x of [-half, half]) for (const z of [-half, half]) { pts.push(new THREE.Vector3(x, -0.45, z)); pts.push(new THREE.Vector3(x, 0, z)); }
    for (const x of [-3.5, 3.5]) for (const z of [-3.5, 3.5]) pts.push(new THREE.Vector3(x, 1.5, z));
    const el = this.view.elevation;
    const dir = new THREE.Vector3(0, Math.sin(el), Math.cos(el));
    const target = new THREE.Vector3(0, 0.1, 0);
    const margin = 0.88;
    const measure = (d) => {
      cam.position.copy(target).addScaledVector(dir, d);
      cam.lookAt(target);
      cam.updateMatrixWorld();
      cam.updateProjectionMatrix();
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      const v = new THREE.Vector3();
      for (const p of pts) {
        v.copy(p).project(cam);
        minX = Math.min(minX, v.x); maxX = Math.max(maxX, v.x); minY = Math.min(minY, v.y); maxY = Math.max(maxY, v.y);
      }
      return { minX, maxX, minY, maxY };
    };
    let lo = 4, hi = 120;
    for (let i = 0; i < 28; i++) {
      const mid = (lo + hi) / 2;
      const b = measure(mid);
      if (b.maxX - b.minX <= 2 * sx * margin && b.maxY - b.minY <= 2 * sy * margin) hi = mid; else lo = mid;
    }
    const b = measure(hi);
    this.distance = hi;
    const stageCx = ((s.x + s.w / 2) / w) * 2 - 1;
    const stageCy = 1 - ((s.y + s.h / 2) / h) * 2;
    this.shift = { x: stageCx - (b.minX + b.maxX) / 2, y: stageCy - (b.minY + b.maxY) / 2 };
    this.placeCamera();
  }

  placeCamera() {
    const cam = this.camera;
    const v = this.view;
    const az = v.azimuth + v.drag + v.drift;
    const el = Math.min(1.25, Math.max(0.5, v.elevation + v.dragElevation));
    const target = new THREE.Vector3(0, 0.1, 0);
    cam.position.set(
      target.x + Math.sin(az) * Math.cos(el) * this.distance,
      target.y + Math.sin(el) * this.distance,
      target.z + Math.cos(az) * Math.cos(el) * this.distance,
    );
    cam.lookAt(target);
    cam.updateMatrixWorld();
    cam.updateProjectionMatrix();
    cam.projectionMatrix.elements[8] = -this.shift.x;
    cam.projectionMatrix.elements[9] = -this.shift.y;
    cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
  }

  // Turns the table to put `side` at the near edge; an eased orbit unless motion is reduced.
  setView(side, { animate = true } = {}) {
    const goal = side === "b" ? Math.PI : 0;
    const from = this.view.azimuth;
    let delta = goal - from;
    while (delta > Math.PI) delta -= 2 * Math.PI;
    while (delta < -Math.PI) delta += 2 * Math.PI;
    if (Math.abs(delta) < 1e-3) return Promise.resolve();
    if (!animate || this.reduced) { this.view.azimuth = goal; return Promise.resolve(); }
    const dragFrom = this.view.drag;
    return this.tweens.add(1.2, (t) => {
      const k = ease.inOut(t);
      this.view.azimuth = from + delta * k;
      this.view.drag = dragFrom * (1 - k);
      this.view.dragElevation *= 1 - k;
    });
  }

  get side() { return Math.cos(this.view.azimuth) < 0 ? "b" : "w"; }

  // Places every piece of a chess.js board() instantly, keeping the meshes that are already in the right place.
  setPosition(rows) {
    this.tweens.finishAll();
    const want = new Map();
    rows.forEach((row) => row.forEach((cell) => { if (cell) want.set(cell.square, cell); }));
    for (const [sq, p] of this.pieces) {
      const w = want.get(sq);
      if (!w || w.type !== p.type || w.color !== p.color || p.tipped) { this.scene.remove(p.group); this.pieces.delete(sq); }
    }
    for (const [sq, cell] of want) {
      if (this.pieces.has(sq)) continue;
      const p = new Piece(cell.type, cell.color, this.materials);
      this.placeAt(p, sq);
      this.scene.add(p.group);
      this.pieces.set(sq, p);
    }
    for (const p of this.pieces.values()) { p.mesh.scale.set(1, 1, 1); p.fade(1); }
  }

  placeAt(p, sq) {
    const [x, z] = squareXZ(sq);
    p.square = sq;
    p.group.position.set(x, 0, z);
    p.group.quaternion.identity();
    p.lift = 0;
    p.tipped = 0;
    p.sinking = 0;
  }

  removePiece(p) {
    this.scene.remove(p.group);
    this.leaving = (this.leaving ?? []).filter((q) => q !== p);
  }

  // Plays one chess.js verbose move; `sound(kind)` fires as each thing lands.
  async play(move, sound = () => {}) {
    const mover = this.pieces.get(move.from);
    if (!mover) return;
    const reduced = this.reduced;
    this.pieces.delete(move.from);
    const capturedSquare = move.flags.includes("e") ? move.to[0] + move.from[1] : move.captured ? move.to : null;
    const victim = capturedSquare ? this.pieces.get(capturedSquare) : null;
    if (victim) { this.pieces.delete(capturedSquare); this.leaving = [...(this.leaving ?? []), victim]; }
    const jobs = [];
    const castle = move.flags.includes("k") ? ["h", "f"] : move.flags.includes("q") ? ["a", "d"] : null;
    if (castle) {
      const rank = move.from[1];
      const rook = this.pieces.get(castle[0] + rank);
      if (rook) {
        this.pieces.delete(castle[0] + rank);
        jobs.push(fly(this, rook, castle[0] + rank, castle[1] + rank, { reduced, hop: 1.5 }).then(() => {
          rook.square = castle[1] + rank;
          this.pieces.set(rook.square, rook);
        }));
      }
    }
    jobs.push(fly(this, mover, move.from, move.to, {
      reduced,
      hop: move.piece === "n" ? 1.6 : 1,
      onLand: () => {
        if (victim) { sink(this, victim, capturedSquare, { reduced }); sound("capture"); }
        else sound("move");
        if (move.promotion) {
          mover.setType(move.promotion);
          if (!reduced) this.tweens.add(0.4, (t) => mover.mesh.scale.setScalar(0.6 + 0.4 * ease.spring(t)));
        }
      },
    }).then(() => {
      mover.square = move.to;
      this.pieces.set(move.to, mover);
    }));
    await Promise.all(jobs);
  }

  setHints(state) {
    this.hintState = state;
    const c = this.hintColors;
    const list = [];
    if (state.last) for (const sq of state.last) list.push({ square: sq, kind: "fill", color: c.last, alpha: 0.5 });
    if (state.selected) list.push({ square: state.selected, kind: "fill", color: c.selected, alpha: 0.65 });
    for (const t of state.targets ?? []) list.push({ square: t.square, kind: t.capture ? "ring" : "dot", color: c.target, alpha: 0.85 });
    if (state.cursor) list.push({ square: state.cursor, kind: "cursor", color: c.cursor, alpha: 1 });
    this.board.setHints(list);
  }

  setCheck(square) { this.checkSquare = square; }

  // Checkmate: the room dims hard and the beaten king tips over; the red square under it stays lit.
  async mate(kingSquare, byFrom) {
    this.exposure.target = 0.34;
    const king = this.pieces.get(kingSquare);
    if (king && !this.reduced) await tip(this, king, byFrom ?? kingSquare);
  }

  undim({ instant = false } = {}) {
    this.exposure.target = 1;
    if (instant) this.exposure.value = 1;
  }

  // Returns the square under a pointer: a piece's body first, then the board itself.
  pick(clientX, clientY) {
    const ndc = new THREE.Vector2((clientX / innerWidth) * 2 - 1, 1 - (clientY / innerHeight) * 2);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.camera);
    const meshes = [...this.pieces.values()].map((p) => p.mesh);
    const hit = ray.intersectObjects(meshes, false)[0];
    if (hit) return hit.object.userData.piece.square;
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const p = new THREE.Vector3();
    return ray.ray.intersectPlane(plane, p) ? xzSquare(p.x, p.z) : null;
  }

  // Where a square sits on screen, for the promotion choice.
  screenOf(square) {
    const [x, z] = squareXZ(square);
    const v = new THREE.Vector3(x, 0.6, z).project(this.camera);
    return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (0.5 - v.y * 0.5) * innerHeight };
  }

  // Pieces in marble when the frame rate cannot carry glass.
  useMarble() {
    if (this.material === "marble") return;
    this.material = "marble";
    this.marble = marbleMaterials(this.tokens);
    this.materials = this.marble;
    for (const p of this.pieces.values()) p.setMaterials(this.materials);
    this.emit("quality", "marble");
  }

  // Watches the first seconds of frames and steps the work down until the table holds its frame rate.
  watchFrames(dt) {
    if (this.qualityDone) return;
    this.frameTimes.push(dt);
    if (this.frameTimes.length < 90) return;
    const sorted = [...this.frameTimes].sort((a, b) => a - b);
    const p80 = sorted[Math.floor(sorted.length * 0.8)];
    this.frameTimes = [];
    const ratio = this.renderer.getPixelRatio();
    if (p80 > 24 && ratio > 1.25) { this.renderer.setPixelRatio(Math.max(1, ratio - 0.5)); this.resize(); return; }
    if (p80 > 24 && this.material === "glass") { this.useMarble(); return; }
    this.qualityDone = true;
  }

  frame(ms) {
    const now = ms / 1000;
    const dt = this.last ? now - this.last : 0;
    this.last = now;
    this.now = now;
    if (dt > 0) this.watchFrames(dt * 1000);
    this.tweens.tick(now);
    this.emit("frame", now);

    const e = this.exposure;
    e.value += (e.target - e.value) * Math.min(1, dt * 2.2);
    this.renderer.toneMappingExposure = e.value;

    if (this.checkSquare) {
      const pulse = this.reduced ? 1 : 0.5 + 0.5 * Math.sin(now * 5.2);
      this.board.setCheck(this.checkSquare, pulse);
    } else this.board.setCheck(null);
    this.board.tick(now);
    this.dust.tick(now);

    const shadows = [];
    const add = (p) => {
      const g = p.group.position;
      shadows.push({ x: g.x, z: g.z, lift: p.lift, radius: p.radius, alpha: (1 - p.sinking) * (1 - p.tipped * 0.6) });
    };
    for (const p of this.pieces.values()) add(p);
    for (const p of this.leaving ?? []) add(p);
    this.board.setShadows(shadows);

    this.placeCamera();
    // The room travels with the camera, so it always surrounds it at any distance.
    this.room.position.copy(this.camera.position);
    this.renderer.render(this.scene, this.camera);
  }
}
