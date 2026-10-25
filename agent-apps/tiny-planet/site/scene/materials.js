// One named export per look. Colors come from the theme tokens; shared uniforms (time, sway) tick from world.js.
import * as THREE from "three";

export const shared = {
  time: { value: 0 },
  sway: { value: 1 },
};

export function terrainMaterial() {
  return new THREE.MeshLambertMaterial({ vertexColors: true });
}

// Flora sways in the wind: the offset grows with height above the root, and each instance has its own phase.
export function floraMaterial() {
  const material = new THREE.MeshLambertMaterial({ vertexColors: true });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = shared.time;
    shader.uniforms.uSway = shared.sway;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uTime;\nuniform float uSway;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
#ifdef USE_INSTANCING
        vec3 rootP = instanceMatrix[3].xyz;
        float phase = uTime * 1.6 + rootP.x * 0.37 + rootP.y * 0.23 + rootP.z * 0.31;
        float bend = max(transformed.y, 0.0) * max(transformed.y, 0.0) * 0.045 * uSway;
        transformed.x += sin(phase) * bend;
        transformed.z += cos(phase * 0.8) * bend * 0.6;
#endif`,
      );
  };
  material.customProgramCacheKey = () => "flora-sway";
  return material;
}

export function stoneMaterial() {
  return new THREE.MeshLambertMaterial({ vertexColors: true });
}

// The sea: faceted like the land. Its vertices rise and fall in slow swells, and flat shading turns each triangle
// into a facet that catches the sun on its own; each facet takes one depth tint from the sea floor under it. One
// clean band of foam runs where the floor rises to the shore, and lava seas add an emissive glow.
export function seaMaterial(colors, glow) {
  const material = new THREE.MeshPhongMaterial({
    color: colors.worldSea,
    specular: new THREE.Color(0.14, 0.14, 0.13),
    shininess: 46,
    flatShading: true,
    transparent: true,
    opacity: 0.94,
  });
  const uniforms = {
    uTime: shared.time,
    uSway: shared.sway,
    uDeep: { value: colors.worldSeaDeep },
    uShallow: { value: colors.worldSea },
    uFoam: { value: colors.worldFoam },
    uGlow: { value: glow },
  };
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
uniform float uTime;
uniform float uSway;
attribute float aDepth;
varying float vDepth;
flat varying float vFaceDepth;
flat varying vec3 vFacePos;`,
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        vDepth = aDepth;
        vFaceDepth = aDepth;
        vFacePos = position;
        float swell = sin(dot(position, vec3(0.31, 0.24, 0.17)) * 1.7 + uTime * 1.3)
          + sin(dot(position, vec3(-0.13, 0.29, 0.22)) * 2.3 - uTime * 1.05);
        transformed += normalize(position) * swell * 0.06 * uSway;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
uniform float uTime;
uniform vec3 uDeep;
uniform vec3 uShallow;
uniform vec3 uFoam;
uniform float uGlow;
varying float vDepth;
flat varying float vFaceDepth;
flat varying vec3 vFacePos;`,
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        float shallow = smoothstep(-2.8, -0.2, vFaceDepth);
        float facet = fract(sin(dot(vFacePos, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
        diffuseColor.rgb = mix(uDeep, uShallow, shallow) * (0.96 + facet * 0.06);
        float edge = -0.3 + 0.04 * sin(uTime * 1.6);
        float foam = smoothstep(edge - 0.035, edge, vDepth);
        diffuseColor.rgb = mix(diffuseColor.rgb, uFoam, foam * 0.92);
        diffuseColor.a = mix(0.97, 0.86, shallow) + foam * 0.1;`,
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        totalEmissiveRadiance += uGlow * (mix(uDeep, uShallow, shallow) * 0.75 + uFoam * foam * 0.9);`,
      );
  };
  material.customProgramCacheKey = () => "sea";
  return material;
}

// The sky dome. Near the ground the gradient runs from the planet's visible edge (which dips below the level of the
// eye on a planet this small) up to the zenith; from orbit it runs up the screen, from the warm horizon color at
// the bottom to a deep top. The sun's disk and halo and the moon's glow are drawn into it.
export function skyMaterial() {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    depthTest: false,
    fog: false,
    uniforms: {
      uUp: { value: new THREE.Vector3(0, 1, 0) },
      uDip: { value: 0 },
      uSun: { value: new THREE.Vector3(0, 1, 0) },
      uZenith: { value: new THREE.Color() },
      uHorizon: { value: new THREE.Color() },
      uSpaceTop: { value: new THREE.Color() },
      uSunColor: { value: new THREE.Color() },
      uGlow: { value: 1 },
      uSunVisible: { value: 1 },
      uMoon: { value: new THREE.Vector3(0, -1, 0) },
      uMoonColor: { value: new THREE.Color() },
      uMoonGlow: { value: 0 },
      uOrbit: { value: 0 },
      uTight: { value: 1 },
      uRes: { value: new THREE.Vector2(1, 1) },
    },
    vertexShader: `
      varying vec3 vDir;
      void main() {
        vDir = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform vec3 uUp;
      uniform float uDip;
      uniform vec3 uSun;
      uniform vec3 uZenith;
      uniform vec3 uHorizon;
      uniform vec3 uSpaceTop;
      uniform vec3 uSunColor;
      uniform float uGlow;
      uniform float uSunVisible;
      uniform vec3 uMoon;
      uniform vec3 uMoonColor;
      uniform float uMoonGlow;
      uniform float uOrbit;
      uniform float uTight;
      uniform vec2 uRes;
      varying vec3 vDir;
      void main() {
        vec3 d = normalize(vDir);
        float y = (dot(d, uUp) + uDip) / (1.0 + uDip);
        vec3 ground = mix(uHorizon, uZenith, pow(clamp(y, 0.0, 1.0), 0.5));
        float sy = clamp(gl_FragCoord.y / uRes.y, 0.0, 1.0);
        vec3 orbit = mix(uHorizon, uZenith, smoothstep(0.0, 0.62, sy));
        orbit = mix(orbit, uSpaceTop, smoothstep(0.45, 1.0, sy));
        vec3 col = mix(ground, orbit, uOrbit);
        float s = max(dot(d, uSun), 0.0);
        float halo = pow(s, 5.0 * uTight) * 0.22 + pow(s, 36.0 * uTight) * 0.36 + pow(s, 400.0 * uTight) * 0.45;
        col += uSunColor * halo * uGlow;
        float disk = smoothstep(1.0 - 0.0014 / (uTight * uTight), 1.0 - 0.0009 / (uTight * uTight), s);
        col = mix(col, uSunColor * 4.0, disk * uSunVisible);
        float m = max(dot(d, uMoon), 0.0);
        col += uMoonColor * (pow(m, 900.0) * 0.5 + pow(m, 60.0) * 0.12) * uMoonGlow;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function starsMaterial(pixelRatio) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    fog: false,
    blending: THREE.AdditiveBlending,
    uniforms: { uNight: { value: 0 }, uTime: shared.time, uScale: { value: pixelRatio } },
    vertexShader: `
      attribute float aSize;
      attribute float aPhase;
      uniform float uTime;
      uniform float uScale;
      varying float vTwinkle;
      void main() {
        vTwinkle = 0.65 + 0.35 * sin(uTime * (1.2 + aPhase) + aPhase * 17.0);
        gl_PointSize = aSize * uScale;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float uNight;
      varying float vTwinkle;
      void main() {
        vec2 p = gl_PointCoord - 0.5;
        float a = smoothstep(0.5, 0.1, length(p));
        gl_FragColor = vec4(vec3(1.0, 0.97, 0.92) * a * uNight * vTwinkle, 1.0);
      }`,
  });
}

// The atmosphere: the inside of a shell larger than the highest peak, drawn behind the planet, depth-tested against
// it, and added onto the sky, so it glows only where the view ray misses the land: a bright band hugging the
// planet's outline that fades out toward the shell, with the land crisp right out to its edge. It is brightest on the side toward the sun,
// and at dusk that side burns in the sun's color. The thickness comes from how close each view ray passes to the
// planet's center.
export function rimMaterial(color) {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
    uniforms: {
      uColor: { value: color.clone() },
      uSunColor: { value: new THREE.Color() },
      uSunDir: { value: new THREE.Vector3(0, 1, 0) },
      uCam: { value: new THREE.Vector3() },
      uIntensity: { value: 1 },
      uDusk: { value: 0 },
      uPlanet: { value: 20 },
      uShell: { value: 26.4 },
    },
    vertexShader: `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: `
      uniform vec3 uColor;
      uniform vec3 uSunColor;
      uniform vec3 uSunDir;
      uniform vec3 uCam;
      uniform float uIntensity;
      uniform float uDusk;
      uniform float uPlanet;
      uniform float uShell;
      varying vec3 vWorld;
      void main() {
        vec3 v = normalize(vWorld - uCam);
        vec3 closest = uCam - v * dot(uCam, v);
        float b = length(closest);
        float thick = pow(clamp((uShell - b) / (uShell - uPlanet), 0.0, 1.0), 2.6);
        // The sun's direction across the screen: which side of the disk faces it.
        vec3 across = uSunDir - v * dot(uSunDir, v);
        float side = dot(closest / max(b, 1e-3), across / max(length(across), 1e-3)) * 0.5 + 0.5;
        // Light from behind the planet scatters forward through the thin air at its edge.
        float behind = max(dot(v, uSunDir), 0.0);
        float lit = mix(0.35 - uDusk * 0.12, 1.2, smoothstep(0.05, 0.95, side)) + behind * uDusk * 0.6;
        float burn = uDusk * smoothstep(0.3, 0.95, side) * mix(0.75, 1.0, behind);
        // At dusk the whole ring takes the sun's amber, deepest and brightest on the sun's side.
        vec3 col = mix(uColor, uSunColor, max(burn, uDusk * 0.75)) * (1.0 + burn * 2.2);
        float a = clamp(thick * lit * uIntensity, 0.0, 1.0);
        gl_FragColor = vec4(col * a * 0.85, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function gemMaterial(color) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 2.6,
    roughness: 0.18,
    metalness: 0.1,
    flatShading: true,
  });
}

// A light column: a white-hot core bright enough to bloom, soft at its edges, fading toward the top, with a slow
// upward shimmer.
export function beamMaterial(color) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    fog: false,
    uniforms: { uColor: { value: color.clone() }, uTime: shared.time, uFade: { value: 1 } },
    vertexShader: `
      varying vec2 vUv;
      varying float vEdge;
      void main() {
        vUv = uv;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vec3 n = normalize(normalMatrix * normal);
        vEdge = abs(dot(n, normalize(-mv.xyz)));
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uFade;
      varying vec2 vUv;
      varying float vEdge;
      void main() {
        float top = pow(1.0 - vUv.y, 1.4);
        float shimmer = 0.8 + 0.2 * sin(vUv.y * 40.0 - uTime * 3.0);
        float core = pow(vEdge, 7.0) * 3.2;
        float a = top * (pow(vEdge, 1.5) + core) * shimmer * uFade;
        gl_FragColor = vec4(uColor * a * 1.2 + vec3(core * top * 0.35 * uFade), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function glowMaterial(color) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.5,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
  });
}

// A soft dark disk on the ground: darkest in the middle, fading to nothing at its rim.
export function contactShadowMaterial() {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
    fog: false,
    uniforms: { uOpacity: { value: 0.5 } },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        float r = length(vUv - 0.5) * 2.0;
        float a = (1.0 - smoothstep(0.15, 1.0, r)) * uOpacity;
        gl_FragColor = vec4(0.0, 0.0, 0.0, a);
      }`,
  });
}

export function explorerMaterial(color) {
  return new THREE.MeshLambertMaterial({ color });
}

// The moon: a full disk with darker seas, its edge dimming slightly toward the limb.
export function moonMaterial(color) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    fog: false,
    uniforms: { uColor: { value: color.clone() }, uOpacity: { value: 1 } },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vView;
      varying vec3 vPos;
      void main() {
        vPos = position;
        vec4 view = modelViewMatrix * vec4(position, 1.0);
        vNormal = normalize(normalMatrix * normal);
        vView = normalize(-view.xyz);
        gl_Position = projectionMatrix * view;
      }`,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      varying vec3 vNormal;
      varying vec3 vView;
      varying vec3 vPos;
      float blot(vec3 p, vec3 c, float r) {
        return 1.0 - smoothstep(r * 0.55, r, length(p - c));
      }
      void main() {
        vec3 p = normalize(vPos);
        float seas = blot(p, vec3(0.35, 0.45, 0.82), 0.42) + blot(p, vec3(-0.3, 0.1, 0.95), 0.33)
          + blot(p, vec3(0.05, -0.45, 0.89), 0.3) + blot(p, vec3(-0.55, 0.55, 0.62), 0.22);
        float limb = mix(0.72, 1.0, pow(max(dot(vNormal, vView), 0.0), 0.5));
        vec3 col = uColor * mix(1.0, 0.72, clamp(seas, 0.0, 1.0)) * limb;
        gl_FragColor = vec4(col, uOpacity);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}
