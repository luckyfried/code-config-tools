// Lights: daylight from the surface that fades with depth, the sub's two headlights with additive cones that catch
// the snow, one lure light the nearest anglerfish carries, and the creatures' glow that rims the sub in the deep.
import * as THREE from "three";
import { shared } from "./materials.js";

export const HEADLIGHT = { range: 46, angle: 0.4, beamTan: 0.34 };

export function createLights(tokens) {
  const W = tokens.world;
  const group = new THREE.Group();
  group.name = "lights";

  const hemi = new THREE.HemisphereLight(W.sun.clone(), W.rockDark.clone(), 2);
  const sun = new THREE.DirectionalLight(W.sun.clone(), 2.4);
  sun.position.set(12, 100, 6);
  group.add(hemi, sun, sun.target);

  const lure = new THREE.PointLight(W.lure.clone(), 0, 14, 1.6);
  lure.name = "lureLight";
  group.add(lure);

  // The vent field's own warm light, so the chimneys and the crabs read in the deepest water.
  const vent = new THREE.PointLight(W.vent.clone(), 0, 70, 1.3);
  vent.name = "ventLight";
  group.add(vent);

  // The creatures' glow on the sub: a cool light behind it from the camera, so the hull keeps its shape in the dark.
  const glow = new THREE.PointLight(W.glow.clone(), 0, 22, 1.4);
  glow.name = "glowLight";
  group.add(glow);

  return { group, hemi, sun, lure, vent, glow };
}

/** Two spotlights and their visible beams, parented to the sub at its lamp lenses. */
export function createHeadlights(tokens, sub) {
  const W = tokens.world;
  const lamps = [];
  // The visible beam: a cone shell wide enough to hold the soft edge, shaded per pixel from where the view ray passes
  // closest to the lamp's axis, so the light falls off smoothly across the beam and along its length, and never ends.
  const L = HEADLIGHT.range;
  const beamGeo = new THREE.ConeGeometry(HEADLIGHT.beamTan * L * 1.9, L, 48, 1, true);
  beamGeo.translate(0, -L / 2, 0);
  beamGeo.rotateX(-Math.PI / 2);
  const beamMat = new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: W.headlight.clone() },
      uTime: shared.uTime,
      uLength: { value: L },
      uTan: { value: HEADLIGHT.beamTan },
      uStrength: { value: 1 },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      varying vec3 vApex;
      varying vec3 vAxis;
      void main() {
        vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
        vApex = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
        vAxis = normalize(mat3(modelMatrix) * vec3(0.0, 0.0, 1.0));
        gl_Position = projectionMatrix * viewMatrix * vec4(vWorld, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uLength;
      uniform float uTan;
      uniform float uStrength;
      varying vec3 vWorld;
      varying vec3 vApex;
      varying vec3 vAxis;
      void main() {
        vec3 rd = normalize(vWorld - cameraPosition);
        vec3 w0 = cameraPosition - vApex;
        float b = dot(rd, vAxis);
        float d = dot(rd, w0);
        float e = dot(vAxis, w0);
        float den = max(1.0 - b * b, 1e-3);
        float tRay = max((b * e - d) / den, 0.0);
        float sAxis = clamp(e + b * tRay, 0.0, uLength);
        vec3 onRay = cameraPosition + rd * tRay;
        float dist = length(onRay - (vApex + vAxis * sAxis));
        float r = max(uTan * sAxis, 0.04);
        float across = exp(-(dist * dist) / (r * r) * 2.4);
        float along = sAxis / uLength;
        float fall = smoothstep(0.0, 0.03, along) * pow(1.0 - along, 2.2) / (1.0 + sAxis * 0.06);
        float shimmer = 0.9 + 0.1 * sin(dot(onRay, vec3(1.3, 1.9, 0.7)) + uTime * 0.5);
        gl_FragColor = vec4(uColor * across * fall * shimmer * 0.26 * uStrength, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.FrontSide,
  });
  for (const side of [-1, 1]) {
    const spot = new THREE.SpotLight(W.headlight.clone(), 260, HEADLIGHT.range, HEADLIGHT.angle, 0.55, 1.35);
    spot.position.set(side * 0.66, -0.36, 1.4);
    spot.target.position.set(side * 1.4, -1.6, 20);
    sub.add(spot, spot.target);
    const beam = new THREE.Mesh(beamGeo, beamMat);
    beam.position.copy(spot.position);
    beam.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(new THREE.Vector3(), spot.target.position.clone().sub(spot.position), new THREE.Vector3(0, 1, 0)));
    beam.rotateY(Math.PI);
    beam.name = "headlightBeam";
    beam.renderOrder = 5;
    sub.add(beam);
    lamps.push({ spot, beam });
  }
  return {
    lamps,
    beamMat,
    /** World position and direction of each lamp, for the snow to brighten inside the beams. */
    write(posOut, dirOut) {
      for (let i = 0; i < lamps.length; i++) {
        const { spot } = lamps[i];
        spot.getWorldPosition(posOut[i]);
        spot.target.getWorldPosition(dirOut[i]);
        dirOut[i].sub(posOut[i]).normalize();
      }
    },
    setOn(on) {
      // Intensity, not visibility: a light leaving the scene would recompile every lit material.
      for (const { spot, beam } of lamps) {
        spot.intensity = on ? 260 : 0;
        beam.visible = on;
      }
    },
  };
}
