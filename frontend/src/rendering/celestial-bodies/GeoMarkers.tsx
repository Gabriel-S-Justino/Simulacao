import { useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import type { EarthEvent } from "../../types/sources";
import { EARTH_RADIUS_M, METERS_PER_UNIT, geoToEarthLocal } from "../frames";

const R = EARTH_RADIUS_M / METERS_PER_UNIT;
const LIFT = 1.002;

/**
 * Pontos circulares de tamanho fixo em pixels. Sem teste de profundidade (um quadrado
 * de vários pixels cortaria a esfera perto do limbo); em vez disso, pontos no
 * hemisfério oposto à câmera são descartados no vertex shader.
 */
const markerVertex = /* glsl */ `
  attribute vec3 color;
  uniform float size;
  varying vec3 vColor;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vec3 center = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
    float facing = dot(normalize(world.xyz - center), normalize(cameraPosition - world.xyz));
    vColor = color;
    gl_Position = projectionMatrix * viewMatrix * world;
    gl_PointSize = facing > 0.0 ? size : 0.0;
  }
`;
const markerFragment = /* glsl */ `
  varying vec3 vColor;
  void main() {
    vec2 p = gl_PointCoord - 0.5;
    float r = length(p);
    if (r > 0.5) discard;
    // Preenchimento na cor da categoria com contorno escuro, para contraste sobre a Terra.
    float alpha = 1.0 - smoothstep(0.42, 0.5, r);
    vec3 col = r < 0.32 ? vColor : vec3(0.02);
    gl_FragColor = vec4(col, alpha);
  }
`;

function MarkerMaterial({ size }: { size: number }) {
  const dpr = useThree((s) => s.viewport.dpr);
  const uniforms = useMemo(() => ({ size: { value: size * dpr } }), [size, dpr]);
  return (
    <shaderMaterial
      vertexShader={markerVertex}
      fragmentShader={markerFragment}
      uniforms={uniforms}
      transparent
      depthTest={false}
      depthWrite={false}
    />
  );
}

/** Cores por categoria EONET; categorias não listadas usam a cor neutra. */
export const CATEGORY_COLORS: Record<string, string> = {
  wildfires: "#ff7a45",
  severeStorms: "#7fa7d9",
  volcanoes: "#ff4d4d",
  seaLakeIce: "#bfe6ff",
  floods: "#4da3ff",
  earthquakes: "#e0b84d",
  dustHaze: "#c9a77c",
};
const NEUTRAL = "#cfd6e0";

/** Última geometria de cada evento (posição mais recente informada pela fonte). */
export function eventPoints(events: EarthEvent[]): { lat: number; lon: number; color: string }[] {
  return events.flatMap((e) => {
    const g = e.geometry[e.geometry.length - 1];
    if (!g) return [];
    return [{ lat: g.lat_deg, lon: g.lon_deg, color: CATEGORY_COLORS[e.categories[0]?.id ?? ""] ?? NEUTRAL }];
  });
}

function usePoints(points: { lat: number; lon: number; color: string }[]) {
  const geometry = useMemo(() => {
    const pos = new Float32Array(points.length * 3);
    const col = new Float32Array(points.length * 3);
    const c = new THREE.Color();
    points.forEach((p, i) => {
      pos.set(geoToEarthLocal(p.lat, p.lon, R * LIFT), i * 3);
      c.set(p.color);
      col.set([c.r, c.g, c.b], i * 3);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return g;
  }, [points]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return geometry;
}

export function EventMarkers({ events }: { events: EarthEvent[] }) {
  const points = useMemo(() => eventPoints(events), [events]);
  const geometry = usePoints(points);
  return (
    <points geometry={geometry} renderOrder={2}>
      <MarkerMaterial size={7} />
    </points>
  );
}

/** Subponto da ISS (Open Notify não informa altitude; o marcador fica na superfície). */
export function IssMarker({ lat, lon }: { lat: number; lon: number }) {
  const points = useMemo(() => [{ lat, lon, color: "#ffffff" }], [lat, lon]);
  const geometry = usePoints(points);
  return (
    <points geometry={geometry} renderOrder={3}>
      <MarkerMaterial size={10} />
    </points>
  );
}
