// What stands on the wall besides the moments' photographs: the line (the one thing every cut carries), and in the
// closer the wall of the month's posts as objects in the same space: each other post rising out of the wall as a block
// with its photograph on its face, the moments' cells standing out furthest with their photographs on their faces,
// their sides in the line's red and their shadows on the posts around them, and the line run out under the wall.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, lerp, span} from '../../system/three/motion';
import {DAY_DEPTH, DEPTH, lineCardAt, lineSpanAt, lineYAt, printZAt, risenAt, standOutAt, stateAt, type Reel, type Tile} from './plan';

const MAX = 600;

/** Up to MAX flat quads in one mesh, rewritten each frame: strokes and bars. */
export const useStrokes = (color: THREE.Color, order: number, additive = false) =>
  useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX * 12), 3));
    const idx: number[] = [];
    for (let i = 0; i < MAX; i++) idx.push(i * 4, i * 4 + 3, i * 4 + 1, i * 4 + 1, i * 4 + 3, i * 4 + 2);
    geo.setIndex(idx);
    const mat = new THREE.MeshBasicMaterial({color, toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending});
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = order;
    return {geo, mat, mesh};
  }, [color, order, additive]);

export type Strokes = ReturnType<typeof useStrokes>;

/** Writes axis-aligned rectangles [x0, y0, x1, y1] (wall px) at depth z into the strokes. */
export const fill = (st: Strokes, r: {W: number; H: number}, rects: number[][], z: number) => {
  const pos = st.geo.getAttribute('position') as THREE.BufferAttribute;
  const n = Math.min(MAX, rects.length);
  for (let i = 0; i < n; i++) {
    const [x0, y0, x1, y1] = rects[i];
    const X0 = x0 - r.W / 2, X1 = x1 - r.W / 2, Y0 = r.H / 2 - y0, Y1 = r.H / 2 - y1;
    pos.setXYZ(i * 4, X0, Y0, z);
    pos.setXYZ(i * 4 + 1, X1, Y0, z);
    pos.setXYZ(i * 4 + 2, X1, Y1, z);
    pos.setXYZ(i * 4 + 3, X0, Y1, z);
  }
  pos.needsUpdate = true;
  st.geo.setDrawRange(0, n * 6);
  st.geo.computeBoundingSphere();
};

/** `tileTex`: each closer tile's photograph, in the order of `reel.closer.tiles` (null for a moment's, which is its card). */
type TileTex = (THREE.Texture | null)[];

export const Wall: React.FC<{reel: Reel; t: number; tileTex: TileTex}> = ({reel: r, t, tileTex}) => {
  // the line in the look's own line color, the same color the closing page and the cards set it in
  const lineColor = useMemo(() => new THREE.Color(r.colors.line), [r.colors.line]);
  const level = useStrokes(lineColor, 2000);
  const st = stateAt(r, Math.min(t, r.closer.still));
  const s = st.s;
  const y = lineYAt(r, t);
  const thick = 9 * s;
  const grow = span(t, 0.3, 0.35, bezier([0.3, 0, 0.2, 1]));
  // the line runs across the print the camera is on, just over it and behind the words, so it never crosses a word,
  // and stays over that print as it trims into its cell
  const tl = Math.min(t, r.closer.still);
  const [x0, x1] = lineSpanAt(r, tl);
  const z = r.cards.length ? Math.max(st.print, printZAt(r, lineCardAt(r, tl), tl)) : st.print;
  fill(level, r, grow > 0 ? [[x0, y - thick / 2, lerp(x0, x1, grow), y + thick / 2]] : [], z + 4 * s);
  return (
    <group>
      <Page reel={r} t={t} tileTex={tileTex} />
      <primitive object={level.mesh} />
    </group>
  );
};

/** A unit box standing on its base's back edge: x and y centered on its foot, z from the wall out. */
const unitBox = () => new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0.5);

// how far, in px, the lit rim on the wall shows around a moment's cell once it stands out: the moment reads as lit
// from the front, where its lit sides are edge-on to the camera. Never wider than half the gap between two cells, so
// each moment reads as its own box.
const RIM = 10;
// the scene's key light falls from the upper left: a moment standing out casts its shadow down and to the right, this
// far per px it stands above the posts around it, this soft and this dark
const FALL: [number, number] = [0.35, 0.58];
const SOFT = 22;
const DARK = 0.55;

/** A soft-edged shadow the size of a cell (`w` by `h` px), drawn on a quad SOFT larger each way. */
const shadeOf = (w: number, h: number) => new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, toneMapped: false,
  uniforms: {uSize: {value: new THREE.Vector2(w, h)}, uAlpha: {value: 0}},
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `varying vec2 vUv; uniform vec2 uSize; uniform float uAlpha;
    void main() {
      vec2 p = (vUv - 0.5) * (uSize + ${(2 * SOFT).toFixed(1)});
      vec2 d = abs(p) - uSize * 0.5;
      float o = length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
      gl_FragColor = vec4(0.0, 0.0, 0.0, uAlpha * (1.0 - smoothstep(-0.4 * ${SOFT.toFixed(1)}, ${SOFT.toFixed(1)}, o)));
    }`,
});

/** The photograph cut to `crop` ([x, y, w, h], fractions of it from its top left) for a block's face. */
const faceOf = (texture: THREE.Texture | null, crop: Tile['crop'], fill: string) => {
  if (!texture || !crop) return new THREE.MeshBasicMaterial({color: fill, toneMapped: false});
  const tx = texture.clone();
  const [x, y, w, h] = crop;
  tx.repeat.set(w, h);
  tx.offset.set(x, 1 - y - h);
  tx.needsUpdate = true;
  return new THREE.MeshBasicMaterial({map: tx, toneMapped: false});
};

/** The wall of the month's posts in the closer: each other post rising out of the wall as a block, one after another,
 * its photograph on its face, and each moment's cell standing out as its block with the moment's photograph for its
 * face, its sides lit in the line's red. */
const Page: React.FC<{reel: Reel; t: number; tileTex: TileTex}> = ({reel: r, t, tileTex}) => {
  const geo = useMemo(unitBox, []);
  const rim = useMemo(() => new THREE.PlaneGeometry(1, 1), []);
  const looks = useMemo(() => {
    const lit = (c: string) => new THREE.MeshStandardMaterial({color: c, roughness: 0.55, metalness: 0.0});
    const line = new THREE.Color(r.colors.line);
    // a moment's day: no face of its own (the photograph is its face), lit red sides, the line's red for its top
    const none = new THREE.MeshBasicMaterial({visible: false});
    const side = lit(`#${line.clone().multiplyScalar(0.8).getHexString()}`);
    const cap = new THREE.MeshBasicMaterial({color: line, toneMapped: false});
    return {day: lit(r.colors.column), moment: [side, side, cap, side, none, side]};
  }, [r.colors]);
  // another post's block: the wall's color on its sides, its photograph on its face
  const posts = useMemo(() => r.closer.tiles.map((x, j) => (x.moment ? null :
    [looks.day, looks.day, looks.day, looks.day, faceOf(tileTex[j], x.crop, r.colors.column), looks.day])), [r, looks, tileTex]);
  // a moment's shadow on the posts around it
  const shades = useMemo(() => r.closer.tiles.map((x) => (x.moment ? shadeOf(x.cell[2] - x.cell[0], x.cell[3] - x.cell[1]) : null)), [r]);
  if (t < r.closer.at - 0.2) return null;
  const toX = (x: number) => x - r.W / 2;
  const toY = (y: number) => r.H / 2 - y;
  const out = standOutAt(r, t);
  return (
    <group>
      {r.closer.tiles.map((x, j) => {
        const [x0, y0, x1, y1] = x.cell;
        if (x.moment) {
          const m = RIM * Math.max(0, out) / DEPTH;
          const above = Math.max(0, out - DAY_DEPTH);
          shades[j]!.uniforms.uAlpha.value = DARK * Math.min(1, above / (DEPTH - DAY_DEPTH));
          return out > 0.5 ? (
            <group key={j}>
              <mesh geometry={rim} material={looks.moment[2]} position={[toX((x0 + x1) / 2), toY((y0 + y1) / 2), 1]} scale={[x1 - x0 + 2 * m, y1 - y0 + 2 * m, 1]} />
              <mesh geometry={rim} material={shades[j]!} renderOrder={1500}
                position={[toX((x0 + x1) / 2) + FALL[0] * above, toY((y0 + y1) / 2) - FALL[1] * above, DAY_DEPTH * 1.1 + 1]}
                scale={[x1 - x0 + 2 * SOFT, y1 - y0 + 2 * SOFT, 1]} />
              <mesh geometry={geo} material={looks.moment} castShadow position={[toX((x0 + x1) / 2), toY(y1), 0]} scale={[x1 - x0, y1 - y0, out]} />
            </group>
          ) : null;
        }
        const u = risenAt(x, t);
        if (u <= 0.001) return null;
        return (
          <mesh key={j} geometry={geo} material={posts[j]!} castShadow receiveShadow position={[toX((x0 + x1) / 2), toY(y1), 0]}
            scale={[x1 - x0, y1 - y0, DAY_DEPTH * Math.min(1.1, u)]} />
        );
      })}
    </group>
  );
};
