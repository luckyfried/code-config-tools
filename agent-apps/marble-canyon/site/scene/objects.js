// Small geometry helpers shared by the track, the canyon, and the effects.
import { BufferAttribute, BufferGeometry } from "three";

// Merges indexed geometries that carry position, normal, and uv into one, each transformed by its matrix.
export function mergeGeometries(parts) {
  let vertices = 0;
  let indices = 0;
  for (const { geometry } of parts) {
    vertices += geometry.attributes.position.count;
    indices += geometry.index ? geometry.index.count : geometry.attributes.position.count;
  }
  const position = new Float32Array(vertices * 3);
  const normal = new Float32Array(vertices * 3);
  const uv = new Float32Array(vertices * 2);
  const index = new Uint32Array(indices);
  let v = 0;
  let i = 0;
  for (const { geometry, matrix } of parts) {
    const g = geometry.clone();
    if (matrix) {
      g.applyMatrix4(matrix);
    }
    const p = g.attributes.position;
    const n = g.attributes.normal;
    const t = g.attributes.uv;
    position.set(p.array, v * 3);
    normal.set(n.array, v * 3);
    if (t) uv.set(t.array, v * 2);
    if (g.index) {
      for (let k = 0; k < g.index.count; k += 1) index[i + k] = g.index.array[k] + v;
      i += g.index.count;
    } else {
      for (let k = 0; k < p.count; k += 1) index[i + k] = v + k;
      i += p.count;
    }
    v += p.count;
    g.dispose();
  }
  const out = new BufferGeometry();
  out.setAttribute("position", new BufferAttribute(position, 3));
  out.setAttribute("normal", new BufferAttribute(normal, 3));
  out.setAttribute("uv", new BufferAttribute(uv, 2));
  out.setIndex(new BufferAttribute(index, 1));
  out.computeBoundingSphere();
  return out;
}

// A matrix whose x axis runs along the track, y along its up, z to its right, placed at p.
export function frameMatrix(m, f, p, scaleX = 1, scaleY = 1, scaleZ = 1) {
  const [tx, ty, tz] = f.t;
  const [nx, ny, nz] = f.n;
  const [rx, ry, rz] = f.r;
  m.set(
    tx * scaleX, nx * scaleY, rx * scaleZ, p[0],
    ty * scaleX, ny * scaleY, ry * scaleZ, p[1],
    tz * scaleX, nz * scaleY, rz * scaleZ, p[2],
    0, 0, 0, 1,
  );
  return m;
}
