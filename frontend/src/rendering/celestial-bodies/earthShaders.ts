export const earthVertex = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vPosW = world.xyz;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
  #include <logdepthbuf_vertex>
}
`;

export const earthFragment = /* glsl */ `
#include <logdepthbuf_pars_fragment>
uniform sampler2D dayMap;
uniform sampler2D nightMap;
uniform float hasDay;
uniform float hasNight;
uniform vec3 sunDir;
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;

void main() {
  #include <logdepthbuf_fragment>
  vec3 n = normalize(vNormalW);
  vec3 v = normalize(cameraPosition - vPosW);
  float ndl = dot(n, sunDir);
  float day = smoothstep(-0.08, 0.18, ndl);

  // Sem textura: cor neutra de oceano, sem geografia inventada.
  vec3 fallback = mix(vec3(0.006, 0.02, 0.05), vec3(0.012, 0.04, 0.09), vUv.y);
  vec3 albedo = hasDay > 0.5 ? texture2D(dayMap, vUv).rgb : fallback;
  // Desaturação leve evita o aspecto "plástico" da composição Blue Marble.
  float luma = dot(albedo, vec3(0.299, 0.587, 0.114));
  albedo = mix(vec3(luma), albedo, 0.88);

  // Máscara de oceano aproximada (dominância do azul) para reflexo especular.
  float ocean = hasDay > 0.5 ? smoothstep(0.02, 0.10, albedo.b - max(albedo.r, albedo.g)) : 1.0;
  vec3 h = normalize(sunDir + v);
  float spec = pow(max(dot(n, h), 0.0), 500.0) * ocean * 0.22 * day;

  vec3 lit = albedo * (max(ndl, 0.0) * 1.15 + 0.012) + vec3(1.0, 0.92, 0.78) * spec;

  vec3 lights = hasNight > 0.5 ? texture2D(nightMap, vUv).rgb : vec3(0.0);
  vec3 night = lights * vec3(1.0, 0.78, 0.5) * 1.4 * (1.0 - smoothstep(-0.25, 0.05, ndl));

  // Dispersão atmosférica na borda (aproximação visual de Rayleigh, não física).
  float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);
  vec3 rim = vec3(0.28, 0.52, 1.0) * fres * smoothstep(-0.3, 0.4, ndl) * 0.9;
  // Avermelhamento no terminador.
  vec3 dusk = vec3(1.0, 0.45, 0.2) * fres * (1.0 - abs(ndl * 3.0)) * 0.25 * step(-0.33, ndl) * step(ndl, 0.33);

  gl_FragColor = vec4(lit * day + night + rim + max(dusk, 0.0), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

export const atmosphereFragment = /* glsl */ `
#include <logdepthbuf_pars_fragment>
uniform vec3 sunDir;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  #include <logdepthbuf_fragment>
  vec3 n = normalize(vNormalW);
  vec3 v = normalize(cameraPosition - vPosW);
  float rim = 1.0 - abs(dot(n, v));
  float glow = pow(rim, 4.5);
  float lit = smoothstep(-0.35, 0.5, dot(n, sunDir));
  vec3 col = mix(vec3(0.25, 0.5, 1.0), vec3(0.55, 0.75, 1.0), pow(rim, 8.0));
  gl_FragColor = vec4(col * glow * lit * 1.3, glow * lit);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;
