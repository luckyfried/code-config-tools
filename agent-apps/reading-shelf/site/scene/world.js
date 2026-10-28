// Assembles the reading room: renderer, camera rig, light, the bookcase with its decor, the motes, and the books.
// createWorld({ canvas, tier, tokens, ... }) is the one export; the page drives it through the object it returns.
import * as THREE from "three";
import { createRenderer } from "./renderer.js";
import { tierSettings, createGovernor } from "./quality.js";
import { readTokens } from "./tokens.js";
import { CameraRig } from "./camera.js";
import { createLights } from "./lights.js";
import { createMotes } from "./motes.js";
import { shelfMaterials, roomMaterials, applyRoomTokens } from "./materials.js";
import { CASE, layoutShelf, buildCase, bookDims } from "./shelf.js";
import { createDecorKit, buildDecor, tickDecor, recolorDecor } from "./decor.js";
import { Book } from "./book.js";
import { dominantColor, hash, paintLeftPage, paintRightPage, paintThumb } from "./textures.js";
import { reducedMotion, damp } from "./motion.js";

function bayCount(books) {
  const total = books.reduce((s, b) => {
    const d = bookDims(b);
    return s + (b.status === "reading" ? d.d + 0.04 : d.t + 0.003);
  }, 0);
  return Math.max(2, Math.ceil(total / (CASE.rows * CASE.bayW * 0.6)));
}

function loadImage(url, cross) {
  return new Promise((resolve) => {
    const img = new Image();
    img.decoding = "async";
    if (cross) img.crossOrigin = "anonymous";
    img.onload = () => resolve(img.naturalWidth > 2 ? img : null);
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

export async function createWorld({ canvas, tier, shelf, books, openLibrary, readRect, insets, text }) {
  const settings = tierSettings(tier);
  let tokens = readTokens();
  const renderer = createRenderer(canvas, settings);
  const scene = new THREE.Scene();
  const rig = new CameraRig();
  const lights = createLights(scene, renderer, settings, tokens);
  const room = roomMaterials(tokens, renderer);
  const shelfMats = shelfMaterials(shelf, renderer);
  const kit = createDecorKit(renderer, tokens);
  const motes = createMotes(settings.motes, tokens);
  scene.add(motes.points);
  renderer.setClearColor(tokens.wall);

  // The room: a wall, a floor, and a skirting board.
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(14, 7), room.wall);
  wall.position.set(0, 3.2, -CASE.depth / 2 - 0.004);
  wall.receiveShadow = true;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 6), room.floor);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, 2.8);
  floor.receiveShadow = true;
  const skirting = new THREE.Mesh(new THREE.BoxGeometry(14, 0.11, 0.02), room.trim);
  skirting.position.set(0, 0.055, -CASE.depth / 2 + 0.006);
  skirting.receiveShadow = true;
  scene.add(wall, floor, skirting);

  const dim = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 30),
    new THREE.MeshBasicMaterial({ color: tokens.scrim, transparent: true, opacity: 0, depthWrite: false }),
  );
  dim.position.z = 0.42;
  dim.renderOrder = 10;
  dim.visible = false;
  scene.add(dim);

  const bookObjs = new Map();
  for (const data of books) {
    const book = new Book(data, renderer, settings.atlas);
    bookObjs.set(data.id, book);
    scene.add(book.root);
  }

  const palette = () => ({
    paper: tokens.paper,
    ink: tokens.ink,
    pageAccent: tokens.pageAccent,
    books: tokens.books,
  });

  // Covers: local files first, so the first frame has them; the rest are painted in the theme's colors.
  await Promise.all(
    [...bookObjs.values()].map(async (book) => {
      if (book.data.cover) book.image = await loadImage(book.data.cover, false);
      book.color = (book.image && dominantColor(book.image)) || tokens.books[hash(book.id) % tokens.books.length];
    }),
  );

  let caseObj = null;
  let decorObj = null;
  let geo = null;
  let bays = 0;
  let slots = null;
  let lit = tokens.glowPower > 0.5;

  function rebuildCase(nBays, decor) {
    if (caseObj) {
      scene.remove(caseObj.group);
      caseObj.group.traverse((o) => o.geometry && o.geometry.dispose());
    }
    caseObj = buildCase(geo, shelfMats, room, tokens, renderer);
    scene.add(caseObj.group);
    if (decorObj) {
      scene.remove(decorObj);
      decorObj.traverse((o) => o.geometry && o.geometry.dispose());
    }
    decorObj = buildDecor(kit, decor, geo.front - 0.022, lit);
    scene.add(decorObj);
    bays = nBays;
    const center = new THREE.Vector3(0, geo.height / 2, 0);
    lights.place(geo, center);
    motes.place(geo, center);
    motes.aim(lights.key);
    rig.setGeometry(geo);
  }

  function relayout(sorted, { entrance = false, now = performance.now() / 1000 } = {}) {
    const nBays = bayCount(sorted);
    const result = layoutShelf(sorted, nBays);
    geo = result.geo;
    slots = result.slots;
    if (nBays !== bays || entrance || !caseObj) rebuildCase(nBays, result.decor);
    else {
      // The small objects move while the books are off the shelf.
      const swap = () => {
        scene.remove(decorObj);
        decorObj.traverse((o) => o.geometry && o.geometry.dispose());
        decorObj = buildDecor(kit, result.decor, geo.front - 0.022, lit);
        scene.add(decorObj);
      };
      if (reducedMotion()) swap();
      else setTimeout(swap, 420);
    }
    sorted.forEach((data, i) => {
      const book = bookObjs.get(data.id);
      const slot = slots.get(data.id);
      if (!book || !slot) return;
      book.place(slot, now, { delay: entrance ? 0.02 + i * 0.018 : i * 0.028, dur: entrance ? 0.62 : 1.1, entrance });
      book.syncBookmark(palette());
    });
  }

  function paintAll() {
    for (const book of bookObjs.values()) {
      const color = book.image ? book.color : tokens.books[hash(book.id) % tokens.books.length];
      book.paint({ color, image: book.image, palette: palette() });
    }
  }

  // Open Library covers, fetched as the shelf comes into view, at most two at a time.
  const remote = { queue: [], running: 0, tried: new Set() };
  async function fetchCover(book) {
    remote.running += 1;
    try {
      let url = null;
      if (book.data.isbn) url = `https://covers.openlibrary.org/b/isbn/${book.data.isbn}-L.jpg?default=false`;
      else {
        const q = `https://openlibrary.org/search.json?title=${encodeURIComponent(book.data.title)}&author=${encodeURIComponent(book.data.author)}&limit=1&fields=cover_i`;
        const res = await fetch(q);
        const json = res.ok ? await res.json() : null;
        const id = json && json.docs && json.docs[0] && json.docs[0].cover_i;
        if (id) url = `https://covers.openlibrary.org/b/id/${id}-L.jpg`;
      }
      if (url) {
        const img = await loadImage(url, true);
        if (img) {
          book.image = img;
          book.color = dominantColor(img) || book.color;
          book.paint({ color: book.color, image: img, palette: palette() });
          api.onCover && api.onCover(book.data);
        }
      }
    } catch {
      // No cover reachable: the generated one stays.
    }
    remote.running -= 1;
  }
  function pumpRemote() {
    if (!openLibrary || remote.running >= 2) return;
    const half = rig.visibleWidth() / 2 + 0.3;
    for (const book of bookObjs.values()) {
      if (book.image || remote.tried.has(book.id)) continue;
      if (Math.abs(book.rest.pos.x - rig.x) > half) continue;
      remote.tried.add(book.id);
      fetchCover(book);
      if (remote.running >= 2) return;
    }
  }

  // Sizing
  let width = 1;
  let height = 1;
  let rowMode = tier === "phone";
  function resize() {
    width = canvas.clientWidth || innerWidth;
    height = canvas.clientHeight || innerHeight;
    renderer.setSize(width, height, false);
    rowMode = tier === "phone" || width < 768;
    rig.resize(width, height, rowMode ? "row" : "wall", insets());
    lights.showFixtures(!rowMode);
    motes.resize(height, renderer.getPixelRatio(), rig.camera.fov);
  }

  // Reading
  let reading = null;
  const pages = { left: document.createElement("canvas"), right: document.createElement("canvas") };
  const tmpV = new THREE.Vector3();
  const qTilt = new THREE.Quaternion();
  const qBook = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -Math.PI / 2);

  function readGeometry(book) {
    const rect = readRect();
    const cam = rig.camera;
    const tan = Math.tan((cam.fov * Math.PI) / 360);
    const { h, d } = book.dims;
    const ppm = Math.min((rect.h * 0.78) / h, (rect.w * 0.86) / (2 * d));
    const D = height / (2 * tan * ppm);
    const visH = 2 * D * tan;
    const visW = visH * cam.aspect;
    const cx = ((rect.x + rect.w / 2) / width) * 2 - 1;
    const cy = -(((rect.y + rect.h / 2) / height) * 2 - 1);
    return { D, cx, cy, visW, visH, pageCss: h * ppm };
  }

  function updateReadPose(book) {
    const cam = rig.camera;
    const g = readGeometry(book);
    const fwd = tmpV.set(0, 0, -1).applyQuaternion(cam.quaternion);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(cam.quaternion);
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(cam.quaternion);
    book.readPose.pos
      .copy(cam.position)
      .addScaledVector(fwd, g.D)
      .addScaledVector(right, (g.cx * g.visW) / 2)
      .addScaledVector(up, (g.cy * g.visH) / 2);
    qTilt.setFromEuler(new THREE.Euler(-0.12, 0.05, 0, "XYZ"));
    book.readPose.quat.copy(cam.quaternion).multiply(qTilt).multiply(qBook);
  }

  function preparePages(book) {
    const g = readGeometry(book);
    const { h, d } = book.dims;
    const H = Math.round(Math.min(1400, Math.max(900, g.pageCss * renderer.getPixelRatio() * 1.15)));
    const W = Math.round((H * (d - 0.006)) / (h - 0.007));
    for (const c of [pages.left, pages.right]) {
      c.width = W;
      c.height = H;
    }
    const scale = H / Math.max(120, g.pageCss);
    const words = text(book.data);
    paintLeftPage(pages.left, book.data, words, palette(), scale);
    paintRightPage(pages.right, book.data, words, palette(), scale);
    return scale;
  }

  let pageScale = 1;
  function openBook(book, now = performance.now() / 1000) {
    if (reading && reading !== book) closeBook(now);
    reading = book;
    updateReadPose(book);
    pageScale = preparePages(book);
    book.pageGlow = tokens.glowPower > 0.5 ? 0.42 : 0.18;
    book.buildOpen(pages);
    book.setHover(true);
    book.openBook(now);
    dim.visible = true;
  }

  function closeBook(now = performance.now() / 1000) {
    if (!reading) return;
    reading.closeBook(now);
    reading.setHover(false);
    reading = null;
  }

  // Picking
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function pick(clientX, clientY) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, rig.camera);
    const targets = [];
    for (const b of bookObjs.values()) {
      if (b.open && b.open.group.visible) targets.push(b.open.group);
      else if (b.mesh.visible) targets.push(b.mesh);
    }
    const hit = ray.intersectObjects(targets, true)[0];
    return hit ? hit.object.userData.book || null : null;
  }

  function screenOf(book) {
    const { h } = book.dims;
    tmpV.set(0, h / 2 + 0.01, 0);
    book.mesh.localToWorld(tmpV);
    tmpV.project(rig.camera);
    return { x: ((tmpV.x + 1) / 2) * width, y: ((1 - tmpV.y) / 2) * height, onScreen: tmpV.z < 1 && Math.abs(tmpV.x) < 1.05 };
  }

  // Theme
  function applyTheme() {
    tokens = readTokens();
    lit = tokens.glowPower > 0.5;
    lights.apply(tokens, tier);
    applyRoomTokens(room, tokens);
    motes.apply(tokens);
    recolorDecor(kit, tokens);
    if (caseObj) {
      caseObj.stripMat.color.set(tokens.shadow);
      caseObj.stripMat.opacity = tokens.shadowPower;
      caseObj.softMat.color.set(tokens.shadow);
      caseObj.softMat.opacity = tokens.shadowPower;
    }
    dim.material.color.set(tokens.scrim);
    renderer.setClearColor(tokens.wall);
    if (geo) {
      const center = new THREE.Vector3(0, geo.height / 2, 0);
      lights.place(geo, center);
      motes.aim(lights.key);
    }
    paintAll();
    for (const b of bookObjs.values()) b.syncBookmark(palette());
    if (reading && reading.open) {
      preparePages(reading);
      reading.open.leftTex.needsUpdate = true;
      reading.open.rightTex.needsUpdate = true;
    }
  }

  // Frame loop
  const governor = createGovernor((level) => {
    if (level === 1) renderer.setPixelRatio(Math.min(1.5, settings.pixelRatio));
    else if (level === 2) renderer.setPixelRatio(1);
    else if (level === 3) {
      renderer.shadowMap.enabled = false;
      lights.key.castShadow = false;
    }
    resize();
  });
  let last = performance.now() / 1000;
  let running = true;
  let dimLevel = 0;
  const api = {
    renderer,
    rig,
    books: bookObjs,
    get geo() {
      return geo;
    },
    get reading() {
      return reading;
    },
    get rowMode() {
      return rowMode && !rig.column;
    },
    get columnMode() {
      return rig.column;
    },
    onFrame: null,
    onCover: null,
    resize,
    relayout,
    paintAll,
    applyTheme,
    pick,
    screenOf,
    openBook,
    closeBook,
    refreshPages(book) {
      if (book && book.open) {
        const words = text(book.data);
        book.repaintPages(pages, palette(), words, pageScale);
      }
      if (book) book.syncBookmark(palette());
    },
    thumb(id, target) {
      const book = bookObjs.get(id);
      if (book) paintThumb(target, book.canvas, book.layout);
    },
    start() {
      running = true;
      last = performance.now() / 1000;
      renderer.setAnimationLoop(frame);
    },
    stop() {
      running = false;
      renderer.setAnimationLoop(null);
    },
  };

  function frame() {
    if (!running) return;
    const now = performance.now() / 1000;
    const dt = Math.min(0.1, now - last);
    last = now;
    governor(dt);
    rig.update(dt, now);
    if (reading) updateReadPose(reading);
    let anyOpen = false;
    for (const book of bookObjs.values()) {
      book.update(now, dt, now);
      if (book.state !== "shelf") anyOpen = true;
      book.setLifted(book === reading || book.state !== "shelf");
    }
    const want = reading ? 0.62 : 0;
    dimLevel = reducedMotion() ? want : damp(dimLevel, want, 5, dt);
    dim.material.opacity = dimLevel;
    dim.visible = dimLevel > 0.005 || anyOpen;
    motes.tick(reducedMotion() ? 0 : now);
    tickDecor(kit, now, lit);
    pumpRemote();
    renderer.render(scene, rig.camera);
    if (api.onFrame) api.onFrame(now, dt);
  }

  resize();
  return api;
}
