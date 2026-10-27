// The field's shaders. Every sounding note is a source of circular waves whose wavelength shortens with pitch;
// where two notes' waves meet they add and cancel, so a chord draws its own interference pattern. A press also
// sends one bright front outward. A second, smaller buffer keeps each held note's glow and lets it rise and swirl
// away slowly, which is the trail a held note leaves.

export const MAX = 16;

export const VERTEX = `#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

const SOURCES = `
uniform int uCount;
uniform vec4 uSrc[${MAX}];
uniform vec4 uCol[${MAX}];
`;

export const TRAIL = `#version 300 es
precision highp float;
uniform sampler2D uPrev;
uniform vec2 uRes;
uniform vec2 uScale;
uniform float uTime;
uniform float uDecay;
uniform float uDrift;
uniform float uEmit;
uniform float uMotion;
${SOURCES}
out vec4 outColor;

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec2 swirl = vec2(sin(uv.y * 7.0 + uTime * 0.6), cos(uv.x * 6.0 - uTime * 0.45)) * 0.0011 * uMotion;
  vec4 prev = texture(uPrev, uv - vec2(0.0, uDrift) - swirl) * uDecay;
  vec2 p = uv * uScale;
  vec3 color = vec3(0.0);
  float weight = 0.0;
  for (int i = 0; i < ${MAX}; i++) {
    if (i >= uCount) break;
    vec2 d = p - uSrc[i].xy * uScale;
    float e = uCol[i].a * exp(-dot(d, d) * 150.0) * uEmit;
    color += uCol[i].rgb * e;
    weight += e;
  }
  outColor = prev + vec4(color, weight);
}`;

export const FIELD = `#version 300 es
precision highp float;
uniform sampler2D uTrail;
uniform vec2 uRes;
uniform vec2 uScale;
uniform float uTime;
uniform float uMotion;
uniform float uMode;
uniform vec3 uBg;
uniform vec3 uA;
uniform vec3 uB;
${SOURCES}
out vec4 outColor;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec2 p = uv * uScale;
  float wave = 0.0;
  float weight = 0.0;
  vec3 tint = vec3(0.0);
  float front = 0.0;
  vec3 frontTint = vec3(0.0);
  for (int i = 0; i < ${MAX}; i++) {
    if (i >= uCount) break;
    vec4 s = uSrc[i];
    vec4 c = uCol[i];
    float r = length(p - s.xy * uScale);
    float age = max(uTime - s.z, 0.0);
    float reach = mix(6.0, age * 0.62, uMotion);
    float inside = smoothstep(reach + 0.015, reach - 0.14, r);
    float w = c.a * inside * exp(-r * 2.3);
    wave += w * cos(s.w * (r - uTime * 0.085 * uMotion));
    weight += w;
    tint += c.rgb * w;
    float ring = exp(-pow((r - reach) * 24.0, 2.0)) * exp(-age * 1.15) * uMotion * (0.3 + c.a);
    front += ring;
    frontTint += c.rgb * ring;
  }
  vec4 trail = texture(uTrail, uv);
  vec3 mean = tint / max(weight, 1e-4);
  float fringe = wave * wave * 1.3;
  float body = weight * 0.3;
  float energy = fringe + body + front * 0.85 + trail.a;
  vec3 hue = (mean * (fringe + body) + frontTint * 0.85 + trail.rgb) / max(energy, 1e-4);

  float drift = uTime * 0.06 * uMotion;
  float wash = 0.5 + 0.5 * sin(uv.x * 2.2 + drift + sin(uv.y * 1.8 - drift * 0.8) * 1.4);
  vec3 ambient = mix(uA, uB, wash);
  vec2 v = uv - vec2(0.5, 0.55);
  vec3 color;
  if (uMode < 0.5) {
    float glow = 1.0 - exp(-energy * 1.45);
    color = uBg + ambient * (0.035 + 0.05 * uv.y) + hue * glow * 1.1;
    color += vec3(pow(max(energy - 1.2, 0.0), 2.0) * 0.12);
    color *= 1.0 - dot(v, v) * 0.6;
  } else {
    // On paper the crests are inked hard and the troughs only stained, so each ring and every crossing shows.
    float lines = 1.0 - exp(-(fringe * 2.4 + front * 1.5));
    float stain = 1.0 - exp(-(body + trail.a) * 1.2);
    float ink = clamp(lines * 0.92 + stain * 0.4, 0.0, 1.0);
    vec3 paper = uBg * (1.0 - (1.0 - ambient) * (0.08 + 0.06 * (1.0 - uv.y)));
    vec3 deep = mix(hue, hue * hue, 0.3);
    color = paper * mix(vec3(1.0), deep, ink * 0.94);
    color *= 1.0 - 0.16 * lines;
    color *= 1.0 - dot(v, v) * 0.14;
  }
  float grain = (hash(gl_FragCoord.xy + fract(uTime) * 91.0) - 0.5) * (2.0 / 255.0);
  outColor = vec4(color + grain, 1.0);
}`;
