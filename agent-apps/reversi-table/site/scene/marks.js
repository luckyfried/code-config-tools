// The marks on the board: glowing legal-move dots, the ghost disc and tint of a previewed move, the last move's glow,
// the hint's pulse, and the keyboard cursor.
import {
  Group, Mesh, InstancedMesh, PlaneGeometry, CylinderGeometry, MeshStandardMaterial, MeshBasicMaterial,
  InstancedBufferAttribute, Object3D, Color, DynamicDrawUsage,
} from "three";
import { BLACK, WHITE } from "../game/reversi.js";
import { glowMaterial, instanceAlphaMaterial, setGlowBlend } from "./materials.js";
import { paintGlow, paintCursor } from "./textures.js";
import { DISC_R, DISC_H, DISC_TOP } from "./discs.js";

const at = (square) => ({ x: (square % 8) - 3.5, z: Math.floor(square / 8) - 3.5 });

export function createMarks() {
  const group = new Group();
  const dummy = new Object3D();
  const dotTexture = paintGlow(256, 0.16);
  const haloTexture = paintGlow(256, 0);

  const dotMaterial = instanceAlphaMaterial(new MeshBasicMaterial({ map: dotTexture, color: 0xffffff, toneMapped: false }));
  const dotGeometry = new PlaneGeometry(0.86, 0.86);
  dotGeometry.rotateX(-Math.PI / 2);
  const dotAlpha = new InstancedBufferAttribute(new Float32Array(64), 1);
  dotAlpha.setUsage(DynamicDrawUsage);
  dotGeometry.setAttribute("instanceAlpha", dotAlpha);
  const dots = new InstancedMesh(dotGeometry, dotMaterial, 64);
  dots.frustumCulled = false;
  dots.renderOrder = 2;
  group.add(dots);

  const capMaterial = instanceAlphaMaterial(new MeshStandardMaterial({ color: 0xffffff, roughness: 0.3, metalness: 0 }));
  const capGeometry = new CylinderGeometry(DISC_R * 0.97, DISC_R * 0.97, 0.01, 40);
  const capAlpha = new InstancedBufferAttribute(new Float32Array(64), 1);
  capAlpha.setUsage(DynamicDrawUsage);
  capGeometry.setAttribute("instanceAlpha", capAlpha);
  const caps = new InstancedMesh(capGeometry, capMaterial, 64);
  caps.frustumCulled = false;
  caps.renderOrder = 3;
  for (let i = 0; i < 64; i += 1) caps.setColorAt(i, new Color(0xffffff));
  group.add(caps);

  const ghostMaterial = new MeshStandardMaterial({ color: 0xffffff, roughness: 0.25, transparent: true, opacity: 0.5, depthWrite: false });
  const ghost = new Mesh(new CylinderGeometry(DISC_R, DISC_R, DISC_H * 2, 40), ghostMaterial);
  ghost.visible = false;
  ghost.renderOrder = 3;
  group.add(ghost);

  const flat = new PlaneGeometry(1, 1);
  flat.rotateX(-Math.PI / 2);
  const lastMaterial = glowMaterial(haloTexture);
  const last = new Mesh(flat, lastMaterial);
  last.scale.setScalar(1.7);
  last.renderOrder = 2;
  group.add(last);

  const hintMaterial = glowMaterial(haloTexture);
  const hint = new Mesh(flat, hintMaterial);
  hint.scale.setScalar(1.5);
  hint.renderOrder = 2;
  group.add(hint);

  const cursorMaterial = glowMaterial(paintCursor());
  const cursor = new Mesh(flat, cursorMaterial);
  cursor.scale.setScalar(1);
  cursor.renderOrder = 2;
  group.add(cursor);

  const colors = { [BLACK]: new Color(), [WHITE]: new Color() };

  function applyTokens(tokens) {
    colors[BLACK].set(tokens.discDark);
    colors[WHITE].set(tokens.discLight);
    const glow = new Color(tokens.glow);
    dotMaterial.color = glow;
    lastMaterial.color = glow;
    hintMaterial.color = glow;
    cursorMaterial.color = glow;
    for (const mat of [dotMaterial, lastMaterial, hintMaterial, cursorMaterial]) setGlowBlend(mat, tokens.glowAdd);
  }

  const pose = {};

  /** Draws the marks for `table` at `now`; `cells` lets the tint ride on top of each disc's own lift. */
  function sync(table, now, liftOf) {
    const level = table.legalLevel(now);
    let n = 0;
    for (const square of table.legal) {
      const p = at(square);
      dummy.position.set(p.x, 0.006, p.z);
      dummy.scale.setScalar(0.8 + 0.2 * level);
      dummy.updateMatrix();
      dots.setMatrixAt(n, dummy.matrix);
      dotAlpha.array[n] = level * (table.preview && table.preview.square === square ? 0 : 0.95);
      n += 1;
    }
    dots.count = n;
    dots.instanceMatrix.needsUpdate = true;
    dotAlpha.needsUpdate = true;

    let c = 0;
    const preview = table.preview;
    if (preview) {
      const p = at(preview.square);
      ghost.visible = true;
      ghost.position.set(p.x, DISC_H + 0.02, p.z);
      ghostMaterial.color.copy(colors[preview.color]);
      const pulse = 0.5 + 0.12 * Math.sin(now / 180);
      ghostMaterial.opacity = pulse;
      for (const square of preview.flips) {
        const q = at(square);
        dummy.position.set(q.x, DISC_TOP + 0.008 + liftOf(square), q.z);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
        caps.setMatrixAt(c, dummy.matrix);
        caps.setColorAt(c, colors[preview.color]);
        capAlpha.array[c] = pulse;
        c += 1;
      }
    } else {
      ghost.visible = false;
    }
    // Reduced motion: a disc changing color shows the new face fading in over the old one.
    for (let i = 0; table.reduced && i < 64 && c < 64; i += 1) {
      table.pose(i, now, pose);
      if (!pose.visible || pose.fade <= 0) continue;
      const q = at(i);
      dummy.position.set(q.x, DISC_TOP + 0.006, q.z);
      dummy.scale.setScalar(1.02);
      dummy.updateMatrix();
      caps.setMatrixAt(c, dummy.matrix);
      caps.setColorAt(c, colors[pose.to]);
      capAlpha.array[c] = pose.fade;
      c += 1;
    }
    caps.count = c;
    caps.instanceMatrix.needsUpdate = true;
    if (caps.instanceColor) caps.instanceColor.needsUpdate = true;
    capAlpha.needsUpdate = true;

    const g = table.glowLevel(now);
    last.visible = g > 0.01;
    if (last.visible) {
      const p = at(table.last.square);
      last.position.set(p.x, 0.005, p.z);
      lastMaterial.opacity = g;
    }

    const h = table.hintLevel(now);
    hint.visible = h > 0.01;
    if (hint.visible) {
      const p = at(table.hint.square);
      hint.position.set(p.x, 0.007, p.z);
      hintMaterial.opacity = h;
    }

    cursor.visible = table.cursor.visible;
    if (cursor.visible) {
      const p = at(table.cursor.square);
      cursor.position.set(p.x, 0.009, p.z);
      cursorMaterial.opacity = 0.95;
    }
  }

  return { group, sync, applyTokens };
}
