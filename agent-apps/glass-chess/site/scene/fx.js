// The dust ring a landing piece kicks up: a soft ring of motes that spreads across the lacquer and fades.
import * as THREE from "three";

const VERTEX = /* glsl */`
  varying vec2 vUv;
  void main() {
    vUv = uv * 2.0 - 1.0;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const FRAGMENT = /* glsl */`
  uniform vec3 uColor;
  uniform float uAge;
  uniform float uStrength;
  varying vec2 vUv;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
  void main() {
    if (uAge < 0.0 || uAge > 1.0) discard;
    float r = length(vUv);
    float front = 0.25 + 0.7 * (1.0 - pow(1.0 - uAge, 3.0));
    float ring = exp(-pow((r - front) * 9.0, 2.0));
    float ang = atan(vUv.y, vUv.x);
    float motes = 0.55 + 0.45 * hash(vec2(floor(ang * 18.0), floor(r * 30.0)));
    float a = ring * motes * (1.0 - uAge) * uStrength;
    if (a < 0.004) discard;
    gl_FragColor = vec4(uColor, a);
    #include <colorspace_fragment>
  }`;

export class Dust {
  constructor(color, layer) {
    this.group = new THREE.Group();
    this.rings = [];
    const geo = new THREE.PlaneGeometry(1, 1);
    for (let i = 0; i < 4; i++) {
      const mat = new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: { uColor: { value: color.clone() }, uAge: { value: -1 }, uStrength: { value: 1 } },
        vertexShader: VERTEX, fragmentShader: FRAGMENT,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = 0.012;
      mesh.renderOrder = 3;
      mesh.layers.set(layer);
      this.group.add(mesh);
      this.rings.push({ mesh, start: -10, life: 0.7 });
    }
    this.next = 0;
  }

  setColor(color) {
    for (const r of this.rings) r.mesh.material.uniforms.uColor.value.copy(color);
  }

  burst(x, z, now, size = 1.6, strength = 1) {
    const r = this.rings[this.next++ % this.rings.length];
    r.mesh.position.x = x;
    r.mesh.position.z = z;
    r.mesh.scale.setScalar(size);
    r.mesh.material.uniforms.uStrength.value = strength;
    r.start = now;
  }

  tick(now) {
    for (const r of this.rings) r.mesh.material.uniforms.uAge.value = (now - r.start) / r.life;
  }
}
