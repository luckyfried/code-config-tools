// One named look per surface. The shelf's three finishes are the inputs' "shelf" key; room colors come from the theme.
import * as THREE from "three";
import { woodCanvas, plasterCanvas, beadboardCanvas } from "./textures.js";
import { canvasTexture } from "./renderer.js";

export const SHELF_LOOKS = {
  oak: { base: "#b5824c", grain: "#5e3b1c", kind: "wood", roughness: 0.58, metalness: 0, lip: "#a77542" },
  white: { base: "#efebe3", grain: "#cfc7b8", kind: "lacquer", roughness: 0.34, metalness: 0, lip: "#f6f3ec" },
  "black-steel": { base: "#202124", grain: "#000000", kind: "steel", roughness: 0.36, metalness: 0.55, lip: "#2b2c30" },
};

export function shelfMaterials(name, renderer) {
  const look = SHELF_LOOKS[name] || SHELF_LOOKS.oak;
  const map = canvasTexture(woodCanvas(look.base, look.grain, 7, look.kind), renderer, { repeat: true });
  map.repeat.set(1.2, 1);
  const board = new THREE.MeshStandardMaterial({ map, roughness: look.roughness, metalness: look.metalness });
  const mapV = map.clone();
  mapV.rotation = Math.PI / 2;
  mapV.repeat.set(1, 0.6);
  mapV.needsUpdate = true;
  const post = new THREE.MeshStandardMaterial({ map: mapV, roughness: look.roughness, metalness: look.metalness });
  return { look, board, post };
}

export function roomMaterials(tokens, renderer) {
  const plaster = canvasTexture(plasterCanvas(3), renderer, { repeat: true, srgb: true });
  plaster.repeat.set(5, 2.5);
  const wall = new THREE.MeshStandardMaterial({ color: tokens.wall, map: plaster, roughness: 0.94 });
  const bead = canvasTexture(beadboardCanvas(), renderer, { repeat: true });
  bead.repeat.set(8, 1);
  const back = new THREE.MeshStandardMaterial({ color: tokens.back, map: bead, roughness: 0.8 });
  const trim = new THREE.MeshStandardMaterial({ color: tokens.trim, roughness: 0.55 });
  const floor = new THREE.MeshStandardMaterial({ color: tokens.floor, roughness: 0.7 });
  return { wall, back, trim, floor };
}

export function applyRoomTokens(mats, tokens) {
  mats.wall.color.set(tokens.wall);
  mats.back.color.set(tokens.back);
  mats.trim.color.set(tokens.trim);
  mats.floor.color.set(tokens.floor);
}

export const brass = () => new THREE.MeshStandardMaterial({ color: "#b58a46", roughness: 0.32, metalness: 0.9 });
export const glaze = (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.22, metalness: 0 });
export const matte = (color, roughness = 0.85) => new THREE.MeshStandardMaterial({ color, roughness, metalness: 0 });
