import { useMemo } from "react";
import * as THREE from "three";

/**
 * Campo estelar ILUSTRATIVO (procedural, semente fixa). Não é um catálogo real;
 * a substituição por um catálogo (ex.: Hipparcos/HYG) está planejada.
 */
const COUNT = 9000;

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const vertex = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
attribute float size;
attribute vec3 tint;
varying vec3 vTint;
void main() {
  vTint = tint;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_PointSize = size;
  gl_Position = projectionMatrix * mv;
  #include <logdepthbuf_vertex>
}`;

const fragment = /* glsl */ `
#include <logdepthbuf_pars_fragment>
varying vec3 vTint;
void main() {
  #include <logdepthbuf_fragment>
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  float a = smoothstep(0.5, 0.0, d);
  gl_FragColor = vec4(vTint * a, a);
}`;

export function Starfield() {
  const geometry = useMemo(() => {
    const rand = mulberry32(1977);
    const pos = new Float32Array(COUNT * 3);
    const size = new Float32Array(COUNT);
    const tint = new Float32Array(COUNT * 3);
    const radius = 50_000;
    for (let i = 0; i < COUNT; i++) {
      const u = rand() * 2 - 1;
      const th = rand() * Math.PI * 2;
      let x = Math.sqrt(1 - u * u) * Math.cos(th);
      let y = u;
      let z = Math.sqrt(1 - u * u) * Math.sin(th);
      // Parte das estrelas concentrada numa faixa (sugere o plano galáctico).
      if (rand() < 0.3) {
        y *= 0.12;
        const l = Math.hypot(x, y, z);
        x /= l;
        y /= l;
        z /= l;
      }
      pos.set([radius * x, radius * y, radius * z], i * 3);
      // Distribuição de brilho tipo lei de potência: poucas estrelas brilhantes.
      const m = Math.pow(rand(), 6);
      size[i] = 0.8 + m * 3.2;
      const temp = rand();
      const b = 0.35 + m * 1.4;
      const c = temp < 0.15 ? [1.0, 0.78, 0.6] : temp < 0.55 ? [1.0, 0.95, 0.88] : [0.78, 0.86, 1.0];
      tint.set([c[0]! * b, c[1]! * b, c[2]! * b], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("size", new THREE.BufferAttribute(size, 1));
    g.setAttribute("tint", new THREE.BufferAttribute(tint, 3));
    return g;
  }, []);

  return (
    <points geometry={geometry} frustumCulled={false} renderOrder={-1}>
      <shaderMaterial
        vertexShader={vertex}
        fragmentShader={fragment}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
