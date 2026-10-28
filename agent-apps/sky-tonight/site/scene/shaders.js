// GLSL shared by the scene: the stereographic projection, the sky's color at any direction, and small helpers.
// Every material is a GLSL 3 ShaderMaterial whose geometry holds directions on the celestial sphere; nothing uses
// the camera's matrices, so one projection keeps stars, lines, the Moon, and the ground in register.

export const PROJECTION = /* glsl */ `
uniform mat3 uSky;      // J2000 equatorial to world (x east, y up, z south)
uniform mat3 uView;     // world to view (x right, y up, z back)
uniform float uK;       // css pixels per projected unit
uniform vec2 uHalf;     // half the viewport in css pixels
uniform float uDpr;

vec2 projPx(vec3 v) {
  float s = 2.0 * uK / max(1.0 - v.z, 1e-4);
  return v.xy * s;
}

vec4 pxToClip(vec2 px) {
  return vec4(px / uHalf, 0.0, 1.0);
}

vec3 dirFromFrag(vec2 fragCoord) {
  vec2 px = fragCoord / uDpr - uHalf;
  vec2 q = px / uK;
  float r2 = dot(q, q);
  float d = 4.0 + r2;
  vec3 v = vec3(4.0 * q / d, -(4.0 - r2) / d);
  return transpose(uView) * v;
}
`;

export const SKY_COLOR = /* glsl */ `
uniform vec3 cNightZ;
uniform vec3 cNightH;
uniform vec3 cAstroZ;
uniform vec3 cAstroH;
uniform vec3 cNautZ;
uniform vec3 cNautH;
uniform vec3 cCivilRim;
uniform vec3 cDayZ;
uniform vec3 cDayH;
uniform vec3 cGlow;
uniform float uSunAlt;
uniform vec3 uSunDir;
uniform vec3 uMoonDir;
uniform float uMoonLight;
uniform float uGlowAmt;
uniform float uInkMode;

vec3 skyColor(vec3 d) {
  float h = clamp(d.y, 0.0, 1.0);
  float t1 = smoothstep(-19.0, -12.0, uSunAlt);
  float t2 = smoothstep(-12.0, -5.0, uSunAlt);
  float t3 = smoothstep(-5.0, 1.0, uSunAlt);
  float t4 = smoothstep(0.0, 10.0, uSunAlt);
  vec2 sh = normalize(uSunDir.xz + vec2(1e-5));
  vec2 dh = normalize(d.xz + vec2(1e-5));
  float side = dot(sh, dh) * 0.5 + 0.5;
  float sideW = mix(0.3, 1.0, side * side);

  vec3 zen = cNightZ;
  zen = mix(zen, cAstroZ, t1);
  zen = mix(zen, cNautZ, t2);
  zen = mix(zen, mix(cNautZ, cDayZ, 0.55), t3);
  zen = mix(zen, cDayZ, t4);
  vec3 hor = cNightH;
  hor = mix(hor, cAstroH, t1 * sideW);
  hor = mix(hor, cNautH, t2 * sideW);
  hor = mix(hor, mix(cNautH, cDayH, 0.5), t3);
  hor = mix(hor, cDayH, t4);

  float g = pow(1.0 - h, 3.2);
  vec3 col = mix(zen, hor, g);

  float rim = exp(-h * 8.0) * side * side * t2 * (1.0 - 0.75 * t4);
  col += cCivilRim * rim * 0.9;

  float cs = max(dot(d, uSunDir), 0.0);
  col += cCivilRim * pow(cs, 18.0) * 0.45 * t2 * (1.0 - uInkMode);
  col += vec3(1.0, 0.96, 0.88) * (pow(cs, 900.0) * 3.0 + pow(cs, 60.0) * 0.25) * t4 * (1.0 - uInkMode);

  col = mix(col + cGlow * exp(-h * 7.0) * uGlowAmt, mix(col, cGlow, exp(-h * 7.0) * uGlowAmt * 0.6), uInkMode);

  float cm = max(dot(d, uMoonDir), 0.0);
  col += cNautH * 0.22 * uMoonLight * (1.0 - t4) * (1.0 - 0.35 * g) * (1.0 - uInkMode);
  col += vec3(0.86, 0.9, 1.0) * (pow(cm, 50.0) * 0.12 + pow(cm, 500.0) * 0.22) * uMoonLight * (1.0 - uInkMode);
  return col;
}
`;

export const DITHER = /* glsl */ `
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
`;

export const FULLSCREEN_VERTEX = /* glsl */ `
void main() {
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

// Where the page's panels and the place name sit, in css pixels from the top left: stars, lines, and planets fade
// out under them so text always stands on clear sky. Each rect carries how strongly it hides what is behind it.
export const MASK_COUNT = 4;
export const MASK = /* glsl */ `
uniform vec4 uMask[${MASK_COUNT}];
uniform float uMaskAmt[${MASK_COUNT}];

vec2 pxToPage(vec2 px) {
  return vec2(px.x + uHalf.x, uHalf.y - px.y);
}

float maskAt(vec2 page) {
  float m = 0.0;
  for (int i = 0; i < ${MASK_COUNT}; i++) {
    vec4 r = uMask[i];
    float d = min(min(page.x - r.x, r.z - page.x), min(page.y - r.y, r.w - page.y));
    m = max(m, smoothstep(-14.0, 6.0, d) * uMaskAmt[i]);
  }
  return m;
}
`;
