// The poster wall: each film is a framed plane with its reflection under the floor, a halo behind it in dark rooms,
// and a contact shadow at its foot. Turns follow a spring, so the poster that reaches the front squares up and settles.
import { Group, Mesh, PlaneGeometry, CanvasTexture, Texture, SRGBColorSpace, LinearMipmapLinearFilter, LinearFilter } from "three";
import { posterShared, posterOwn, posterMaterial, haloMaterial, shadowMaterial } from "./materials.js";
import { POSTER_W, POSTER_H, POSTER_BASE, slot, spring } from "../game/motion.js";

function cropFor(w, h) {
  const ia = w / h;
  const ta = POSTER_W / POSTER_H;
  if (ia > ta) {
    const sx = ta / ia;
    return [(1 - sx) / 2, 0, sx, 1];
  }
  const sy = ia / ta;
  return [0, (1 - sy) / 2, 1, sy];
}

export class Wall {
  constructor(scene, renderer) {
    this.scene = scene;
    this.renderer = renderer;
    this.group = new Group();
    scene.add(this.group);
    this.shared = posterShared();
    this.geo = new PlaneGeometry(POSTER_W, POSTER_H);
    this.haloGeo = new PlaneGeometry(POSTER_W * 2.1, POSTER_H * 1.7);
    this.shadowGeo = new PlaneGeometry(POSTER_W * 1.5, 0.9);
    this.items = [];
    this.halo = 0;
    this.shadow = 0;
    this.dim = 0.6;
  }

  setTokens(t) {
    const s = this.shared;
    s.uRim.value.copy(t.rim);
    s.uFrame.value.copy(t.frame);
    s.uDimColor.value.copy(t.dimColor);
    s.uFog.value.copy(t.fog);
    s.uRimStrength.value = t.rimStrength;
    s.uKey.value = t.key;
    s.uReflect.value = t.reflect;
    this.halo = t.additive > 0.5 ? t.halo : 0;
    this.shadow = t.shadow;
    this.dim = t.dim;
    for (const it of this.items) it.halo.material.uniforms.uColor.value.copy(t.rim);
  }

  setFog(near, far) {
    this.shared.uFogNear.value = near;
    this.shared.uFogFar.value = far;
  }

  texture(source) {
    const tex = source instanceof HTMLCanvasElement ? new CanvasTexture(source) : new Texture(source);
    tex.colorSpace = SRGBColorSpace;
    tex.generateMipmaps = true;
    tex.minFilter = LinearMipmapLinearFilter;
    tex.magFilter = LinearFilter;
    tex.anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
    tex.needsUpdate = true;
    return tex;
  }

  setFilms(films, sources) {
    for (const it of this.items) {
      this.group.remove(it.root);
      it.front.material.dispose();
      it.mirror.material.dispose();
      it.halo.material.dispose();
      it.shadowMesh.material.dispose();
      it.tex.dispose();
    }
    this.items = films.map((film, i) => {
      const tex = this.texture(sources[i]);
      const own = posterOwn(tex);
      const front = new Mesh(this.geo, posterMaterial(this.shared, own, false));
      const mirror = new Mesh(this.geo, posterMaterial(this.shared, own, true));
      mirror.scale.y = -1;
      mirror.renderOrder = 1;
      const halo = new Mesh(this.haloGeo, haloMaterial());
      halo.material.uniforms.uColor.value.copy(this.shared.uRim.value);
      halo.position.z = -0.08;
      halo.renderOrder = 3;
      const shadowMesh = new Mesh(this.shadowGeo, shadowMaterial());
      shadowMesh.rotation.x = -Math.PI / 2;
      shadowMesh.position.set(0, 0.003, 0.08);
      shadowMesh.renderOrder = 2;
      front.userData.index = i;
      const root = new Group();
      root.add(front, mirror, halo, shadowMesh);
      this.group.add(root);
      const item = { key: film.key, root, front, mirror, halo, shadowMesh, own, tex, rot: { x: 0, v: 0 }, lift: { x: 0, v: 0 }, placed: false };
      this.crop(item, sources[i]);
      return item;
    });
  }

  crop(item, source) {
    const w = source.naturalWidth || source.width;
    const h = source.naturalHeight || source.height;
    item.own.uCrop.value.set(...cropFor(w, h));
  }

  setSource(i, source) {
    const it = this.items[i];
    if (!it) return;
    it.tex.dispose();
    it.tex = this.texture(source);
    it.own.map.value = it.tex;
    this.crop(it, source);
  }

  // p: the wall's position; spot: { index, on } where on is how fully the spotlight has landed.
  update(dt, p, phone, spot, hover) {
    for (let i = 0; i < this.items.length; i += 1) {
      const it = this.items[i];
      const d = i - p;
      const a = Math.abs(d);
      it.root.visible = a < 7.5;
      if (!it.root.visible) continue;
      const s = slot(d, phone);
      if (!it.placed) {
        it.rot.x = s.rot;
        it.placed = true;
      }
      spring(it.rot, s.rot, 190, 0.5, dt);
      spring(it.lift, hover === i && a < 2.5 ? 0.09 : 0, 220, 0.7, dt);
      const y = POSTER_BASE + POSTER_H / 2 + it.lift.x;
      it.root.position.set(s.x, 0, s.z);
      it.root.rotation.y = it.rot.x;
      it.front.position.y = y;
      it.mirror.position.y = -y;
      it.halo.position.y = y;

      const isSpot = spot.index === i;
      const centered = 1 - Math.min(a, 1);
      const u = it.own;
      u.uBlur.value = Math.min(Math.max(a - 0.1, 0) * 1.8, 3.4);
      u.uRot.value = it.rot.x;
      u.uSpot.value = isSpot ? spot.on : 0;
      u.uDim.value = isSpot ? 0 : this.dim * spot.dimming;
      u.uShine.value = 0.5 + 0.5 * centered;
      it.halo.visible = this.halo > 0 && a < 1.5;
      it.halo.material.uniforms.uLevel.value = this.halo * centered * (0.35 + 0.65 * (isSpot ? spot.on : 0));
      it.shadowMesh.visible = this.shadow > 0;
      it.shadowMesh.material.uniforms.uLevel.value = this.shadow * (1 - Math.min(a * 0.12, 0.5)) * (1 - it.lift.x * 3);
    }
  }

  meshes() {
    return this.items.filter((it) => it.root.visible).map((it) => it.front);
  }

  worldOf(i, out) {
    const it = this.items[i];
    if (!it) return null;
    out.set(it.root.position.x, 0, it.root.position.z);
    return out;
  }
}
