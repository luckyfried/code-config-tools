// Assembles the table scene: renderer, studio light, board, discs, trays, marks, and the camera rig. Its one export
// builds the world for a quality tier and the theme's tokens; the page drives it with a Table model.
import { Scene, Mesh, PlaneGeometry, Color, Raycaster, Vector2, Vector3, Plane, Box3, Fog } from "three";
import { createRenderer } from "./renderer.js";
import { CameraRig } from "./camera.js";
import { loadStudio, createKeyLight, applyLightTokens } from "./lights.js";
import { discMaterial, tableMaterial, glintFace } from "./materials.js";
import { createBoard, BOARD_HALF, FRAME } from "./board.js";
import { discGeometries, DiscPool, discQuaternion, applyDiscTokens, DISC_H } from "./discs.js";
import { createTrays, TABLE_Y } from "./trays.js";
import { createMarks } from "./marks.js";
import { paintTable } from "./textures.js";
import { BLACK, WHITE } from "../game/reversi.js";

export async function createWorld({ host, settings, tokens, envUrl }) {
  const renderer = createRenderer(host, settings);
  const scene = new Scene();
  const rig = new CameraRig();

  const environment = await loadStudio(renderer, envUrl);
  scene.environment = environment;

  const key = createKeyLight(settings);
  scene.add(key, key.target);

  const tableMat = tableMaterial();
  const table = new Mesh(new PlaneGeometry(48, 48), tableMat);
  table.rotation.x = -Math.PI / 2;
  table.position.y = TABLE_Y;
  table.receiveShadow = true;
  scene.add(table);

  const board = createBoard(settings);
  scene.add(board.group);

  const lightMat = discMaterial(settings, 3.2, 0.2);
  const darkMat = discMaterial(settings, 1.5, 0);
  const geometries = discGeometries(settings.segments);
  const boardDiscs = new DiscPool(geometries, lightMat, darkMat, 64);
  const trayDiscs = new DiscPool(geometries, lightMat, darkMat, 128);
  boardDiscs.addTo(scene);
  trayDiscs.addTo(scene);

  const trays = createTrays();
  scene.add(trays.group);
  let layout = trays.build("wide");

  const marks = createMarks();
  scene.add(marks.group);

  let tablePainted = null;
  function applyTokens(next) {
    tokens = next;
    if (tablePainted) tablePainted.dispose();
    tablePainted = paintTable(tokens, settings.tier === "phone" ? 1024 : 2048);
    tableMat.map = tablePainted;
    tableMat.roughness = tokens.tableTexture === "glass" ? 0.35 : tokens.tableTexture === "leather" ? 0.6 : 0.85;
    tableMat.needsUpdate = true;
    scene.background = new Color(tokens.tableEdge);
    scene.fog = new Fog(new Color(tokens.tableEdge), 34, 70);
    scene.environmentIntensity = tokens.env;
    renderer.toneMappingExposure = tokens.exposure;
    applyLightTokens(key, tokens);
    board.applyTokens(tokens);
    applyDiscTokens(lightMat, darkMat, tokens);
    trays.applyTokens(tokens);
    marks.applyTokens(tokens);
  }
  applyTokens(tokens);

  // The framing box: board, trays, stack height, and room for the player cards.
  function contentBox(mode) {
    const edge = BOARD_HALF + FRAME;
    if (mode === "wide") {
      const x = layout.centers[WHITE].x + layout.size.w / 2 + 0.1;
      const rim = Math.max(edge, layout.size.d / 2) + 0.05;
      const near = layout.cardsAbove ? rim : Math.max(rim, layout.anchors[BLACK].z + 0.8);
      const far = layout.cardsAbove ? -layout.anchors[BLACK].z + 1.4 : rim;
      return new Box3(new Vector3(-x, TABLE_Y, -far), new Vector3(x, 1.0, near));
    }
    const z = layout.centers[BLACK].z + layout.size.d / 2;
    return new Box3(new Vector3(-edge, TABLE_Y, -z - 1.7), new Vector3(edge, 0.4, z + 1.7));
  }

  let size = { width: 1, height: 1 };

  /** Frames the table in `rect` (the screen area the page leaves free) for a `wide` or `tall` arrangement. */
  function frame({ width, height, rect, mode, cardsAbove = false, now, immediate }) {
    const above = mode === "wide" && cardsAbove;
    if (mode !== layout.mode || above !== layout.cardsAbove) layout = trays.build(mode, above);
    if (width !== size.width || height !== size.height) {
      renderer.setSize(width, height, false);
      size = { width, height };
    }
    const elevation = mode === "wide" ? (64 * Math.PI) / 180 : (70 * Math.PI) / 180;
    rig.frame({ width, height, rect, box: contentBox(mode), elevation }, now, immediate);
  }

  const pose = {};
  const quat = discQuaternion(WHITE, 0, 1, 0, rig.camera.quaternion.clone());
  const lifts = new Float32Array(64);
  const liftOf = (square) => lifts[square];

  // The face that sends the key light to the eye leans a few degrees toward the key, so the glint sits on each
  // disc's upper left, the way the key light's own highlight falls.
  const glintWorld = new Vector3(-0.07, 1, -0.06).normalize();
  function aimGlint() {
    glintFace.value.copy(glintWorld).transformDirection(rig.camera.matrixWorldInverse);
  }

  function render(model, now) {
    rig.apply(now);
    aimGlint();
    for (let i = 0; i < 64; i += 1) {
      model.pose(i, now, pose);
      lifts[i] = pose.lift;
      if (!pose.visible) {
        boardDiscs.hide(i);
        continue;
      }
      const x = (i % 8) - 3.5;
      const z = Math.floor(i / 8) - 3.5;
      const angle = pose.angle;
      const ax = pose.ax;
      const az = pose.az;
      // A previewed capture lifts each disc that would turn, as if a finger were already under it; its tint rides on top.
      if (angle === 0 && model.preview && model.preview.flips.includes(i)) lifts[i] = 0.07;
      discQuaternion(pose.show, angle, ax, az, quat);
      boardDiscs.set(i, x, DISC_H + lifts[i], z, quat, pose.scale);
    }
    boardDiscs.commit();
    trays.sync(model, now, trayDiscs, 0, BLACK);
    trays.sync(model, now, trayDiscs, 64, WHITE);
    trayDiscs.commit();
    marks.sync(model, now, liftOf);
    renderer.render(scene, rig.camera);
  }

  const raycaster = new Raycaster();
  const ndc = new Vector2();
  const plane = new Plane(new Vector3(0, 1, 0), -DISC_H);
  const hit = new Vector3();

  /** The square under client point (x, y), or -1. */
  function pick(x, y) {
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, rig.camera);
    if (!raycaster.ray.intersectPlane(plane, hit)) return -1;
    const col = Math.floor(hit.x + 4);
    const row = Math.floor(hit.z + 4);
    if (col < 0 || col > 7 || row < 0 || row > 7) return -1;
    return row * 8 + col;
  }

  const v = new Vector3();
  /** Screen position (CSS px) of a world point. */
  function project(point) {
    v.copy(point).project(rig.camera);
    return { x: ((v.x + 1) / 2) * size.width, y: ((1 - v.y) / 2) * size.height };
  }

  function anchors() {
    return {
      [BLACK]: project(layout.anchors[BLACK]),
      [WHITE]: project(layout.anchors[WHITE]),
      below: layout.below,
      center: project(new Vector3(0, 0, 0)),
      top: project(new Vector3(0, 0, -BOARD_HALF)),
      boardWidth: project(new Vector3(BOARD_HALF, 0, 0)).x - project(new Vector3(-BOARD_HALF, 0, 0)).x,
    };
  }

  /** One quality step down: the reflection first, then the pixel ratio. */
  function stepDown(step) {
    if (step === 1) board.dropReflection();
    else if (step === 2) renderer.setPixelRatio(Math.min(settings.pixelRatio, 1.5));
    else renderer.setPixelRatio(1);
    renderer.setSize(size.width, size.height, false);
  }

  async function warm() {
    if (renderer.compileAsync) await renderer.compileAsync(scene, rig.camera);
  }

  return {
    kind: "webgl",
    canvas: renderer.domElement,
    frame,
    render,
    pick,
    anchors,
    applyTokens,
    stepDown,
    warm,
    cameraMoving: (now) => rig.moving(now),
  };
}
