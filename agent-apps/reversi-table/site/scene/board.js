// The board: a lacquered box with a raised frame, the playing face recessed inside it with grooved lines, and a thin
// reflector over the face that gives the lacquer its mirror at the theme's strength.
import { Group, Mesh, PlaneGeometry, Shape, Path, ExtrudeGeometry, Color } from "three";
import { Reflector } from "three/addons/objects/Reflector.js";
import { boardFaceMaterial, lacquerMaterial } from "./materials.js";
import { paintBoard, paintBoardGlow } from "./textures.js";

export const BOARD_HALF = 4;
export const FRAME = 0.5;
export const BASE_DEPTH = 0.42;

function roundedRect(shape, x, y, w, h, r) {
  shape.moveTo(x + r, y);
  shape.lineTo(x + w - r, y);
  shape.quadraticCurveTo(x + w, y, x + w, y + r);
  shape.lineTo(x + w, y + h - r);
  shape.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  shape.lineTo(x + r, y + h);
  shape.quadraticCurveTo(x, y + h, x, y + h - r);
  shape.lineTo(x, y + r);
  shape.quadraticCurveTo(x, y, x + r, y);
  return shape;
}

// The reflection drawn over the face as a thin wash: the mirror image times the theme's strength. The mirror renders
// without the room behind it, so only what stands on the board (the discs, the frame) shows in the lacquer.
const WashShader = {
  name: "ReflectionWash",
  uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null }, opacity: { value: 0.2 } },
  vertexShader: /* glsl */ `
    uniform mat4 textureMatrix;
    varying vec4 vUv;
    #include <common>
    #include <logdepthbuf_pars_vertex>
    void main() {
      vUv = textureMatrix * vec4( position, 1.0 );
      gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
      #include <logdepthbuf_vertex>
    }`,
  fragmentShader: /* glsl */ `
    uniform vec3 color;
    uniform sampler2D tDiffuse;
    uniform float opacity;
    varying vec4 vUv;
    #include <logdepthbuf_pars_fragment>
    void main() {
      #include <logdepthbuf_fragment>
      vec4 base = texture2DProj( tDiffuse, vUv );
      gl_FragColor = vec4( base.rgb * color, opacity * base.a );
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
};

export function createBoard(settings) {
  const group = new Group();
  const lacquer = lacquerMaterial();
  const outer = BOARD_HALF + FRAME;

  const baseShape = roundedRect(new Shape(), -outer, -outer, outer * 2, outer * 2, 0.32);
  const base = new Mesh(
    new ExtrudeGeometry(baseShape, { depth: BASE_DEPTH, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 3, curveSegments: 8 }),
    lacquer,
  );
  base.rotation.x = -Math.PI / 2;
  base.position.y = -BASE_DEPTH - 0.07;
  base.castShadow = true;
  base.receiveShadow = true;
  group.add(base);

  const frameShape = roundedRect(new Shape(), -outer, -outer, outer * 2, outer * 2, 0.32);
  const hole = new Path();
  hole.moveTo(-BOARD_HALF, -BOARD_HALF);
  hole.lineTo(-BOARD_HALF, BOARD_HALF);
  hole.lineTo(BOARD_HALF, BOARD_HALF);
  hole.lineTo(BOARD_HALF, -BOARD_HALF);
  hole.lineTo(-BOARD_HALF, -BOARD_HALF);
  frameShape.holes.push(hole);
  const frame = new Mesh(
    new ExtrudeGeometry(frameShape, { depth: 0.05, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 3, curveSegments: 8 }),
    lacquer,
  );
  frame.rotation.x = -Math.PI / 2;
  frame.position.y = -0.03;
  frame.castShadow = true;
  frame.receiveShadow = true;
  group.add(frame);

  const faceMaterial = boardFaceMaterial();
  const face = new Mesh(new PlaneGeometry(BOARD_HALF * 2, BOARD_HALF * 2), faceMaterial);
  face.rotation.x = -Math.PI / 2;
  face.receiveShadow = true;
  group.add(face);

  let reflector = null;
  if (settings.reflection) {
    const size = Math.round(Math.min(2048, Math.max(innerWidth, innerHeight) * settings.pixelRatio * settings.reflectionScale));
    reflector = new Reflector(new PlaneGeometry(BOARD_HALF * 2, BOARD_HALF * 2), {
      textureWidth: size,
      textureHeight: size,
      clipBias: 0.003,
      multisample: settings.reflectionSamples,
      shader: WashShader,
    });
    reflector.material.transparent = true;
    reflector.material.depthWrite = false;
    reflector.rotation.x = -Math.PI / 2;
    reflector.position.y = 0.002;
    reflector.renderOrder = 1;
    const mirror = reflector.onBeforeRender;
    const clear = new Color();
    reflector.onBeforeRender = (renderer, scene, camera) => {
      const background = scene.background;
      const fog = scene.fog;
      const alpha = renderer.getClearAlpha();
      renderer.getClearColor(clear);
      scene.background = null;
      scene.fog = null;
      renderer.setClearColor(0x000000, 0);
      mirror.call(reflector, renderer, scene, camera);
      renderer.setClearColor(clear, alpha);
      scene.background = background;
      scene.fog = fog;
    };
    group.add(reflector);
  }

  let painted = [];
  function applyTokens(tokens) {
    for (const t of painted) t.dispose();
    const size = settings.tier === "phone" ? 1024 : 2048;
    const map = paintBoard(tokens, size);
    faceMaterial.map = map;
    painted = [map];
    if (tokens.lineGlow > 0) {
      const glow = paintBoardGlow(tokens, size);
      faceMaterial.emissiveMap = glow;
      faceMaterial.emissiveIntensity = tokens.lineGlow;
      painted.push(glow);
    } else {
      faceMaterial.emissiveMap = null;
      faceMaterial.emissiveIntensity = 0;
    }
    faceMaterial.needsUpdate = true;
    lacquer.color = new Color(tokens.rim);
    if (reflector) {
      reflector.material.uniforms.opacity.value = tokens.reflect;
      reflector.material.uniforms.color.value = new Color(0xffffff);
    }
  }

  function dropReflection() {
    if (!reflector) return;
    group.remove(reflector);
    reflector.dispose();
    reflector = null;
  }

  return { group, applyTokens, dropReflection, get reflector() { return reflector; } };
}
