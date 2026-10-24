import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useCatalog } from "../../services/queries";
import { playbackClock, useMission } from "../../stores/missionStore";
import { craftPosition } from "../craftPosition";
import { buildSpacecraft, type PlacedPart } from "./buildModel";
import { createSpacecraftMaterials, disposeMaterials } from "./materials";

/** Escala visual da nave no modo exploração (indicada na interface). */
export const CRAFT_VISUAL_SCALE = 1500;
const UNITS_PER_METER_VISUAL = CRAFT_VISUAL_SCALE / 1_000_000;

const _y = new THREE.Vector3();
const _z = new THREE.Vector3();
const _x = new THREE.Vector3();
const _m = new THREE.Matrix4();
const _sunLocal = new THREE.Vector3();
const _q = new THREE.Quaternion();

export function Spacecraft({ sunDir }: { sunDir: THREE.Vector3 }) {
  const group = useRef<THREE.Group>(null);
  const parts = useMission((s) => s.parts);
  const catalog = useCatalog();
  const materials = useMemo(() => createSpacecraftMaterials(), []);
  useEffect(() => () => disposeMaterials(materials), [materials]);

  const model = useMemo(() => {
    const byId = new Map(catalog.data?.components.map((c) => [c.id, c]) ?? []);
    const placed: PlacedPart[] = [];
    for (const [id, p] of Object.entries(parts)) {
      const component = byId.get(id);
      if (component) placed.push({ component, quantity: p.quantity });
    }
    return buildSpacecraft(placed, materials);
  }, [catalog.data, parts, materials]);
  useEffect(() => () => model.geometries.forEach((g) => g.dispose()), [model]);

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    const st = craftPosition.state;
    g.position.copy(craftPosition.scene);
    // Atitude visual: +Y alinhado à velocidade, +Z para o nadir. Sem modelo de atitude ainda.
    _y.set(st.v[0], st.v[2], -st.v[1]).normalize();
    _z.copy(craftPosition.scene).negate().normalize();
    _x.crossVectors(_y, _z).normalize();
    _z.crossVectors(_x, _y).normalize();
    if (_x.lengthSq() > 0.5) {
      _m.makeBasis(_x, _y, _z);
      g.quaternion.setFromRotationMatrix(_m);
    }
    // Painéis giram em torno do eixo da haste (X local) para encarar o Sol.
    _q.copy(g.quaternion).invert();
    _sunLocal.copy(sunDir).applyQuaternion(_q);
    const angle = Math.atan2(-_sunLocal.z, _sunLocal.y);
    for (const w of model.solarWings) w.rotation.x = angle;
    if (model.plume) {
      const mat = model.plume.material as THREE.MeshBasicMaterial;
      mat.opacity = burnIntensity(playbackClock.t) * 0.55;
    }
  });

  return (
    <group ref={group} scale={UNITS_PER_METER_VISUAL}>
      <primitive object={model.root} />
    </group>
  );
}

/** Intensidade visual da pluma: ativa durante a duração finita estimada de cada queima. */
function burnIntensity(t: number): number {
  const sim = useMission.getState().simulation;
  if (!sim) return 0;
  for (const e of sim.events) {
    if (e.kind !== "burn") continue;
    const half = Math.max((e.data.finite_burn_s ?? 0) / 2, 20);
    const d = Math.abs(t - e.t_s);
    if (d < half) return 1 - d / half;
  }
  return 0;
}
