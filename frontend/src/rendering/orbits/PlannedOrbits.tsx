import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { useMission } from "../../stores/missionStore";
import { EARTH_RADIUS_M, METERS_PER_UNIT } from "../frames";

/** Órbitas inicial e alvo (círculos analíticos dos parâmetros do plano). Pré-visualização. */
export function PlannedOrbits() {
  const plan = useMission((s) => s.plan);
  const lines = useMemo(() => {
    const inc = (plan.inclinationDeg * Math.PI) / 180;
    const make = (altKm: number, color: string, opacity: number) => {
      const r = (EARTH_RADIUS_M + altKm * 1000) / METERS_PER_UNIT;
      const pts: THREE.Vector3[] = [];
      for (let i = 0; i <= 256; i++) {
        const a = (i / 256) * Math.PI * 2;
        // ECI: x = r cos a, y = r sin a cos i, z = r sin a sin i → cena (x, z, -y)
        pts.push(new THREE.Vector3(r * Math.cos(a), r * Math.sin(a) * Math.sin(inc), -r * Math.sin(a) * Math.cos(inc)));
      }
      const g = new THREE.BufferGeometry().setFromPoints(pts);
      const m = new THREE.LineDashedMaterial({ color, transparent: true, opacity, dashSize: 0.15, gapSize: 0.1 });
      const line = new THREE.Line(g, m);
      line.computeLineDistances();
      return line;
    };
    return [make(plan.initialAltitudeKm, "#7fa7d9", 0.45), make(plan.targetAltitudeKm, "#f2c46b", 0.6)];
  }, [plan]);

  useEffect(
    () => () =>
      lines.forEach((l) => {
        l.geometry.dispose();
        (l.material as THREE.Material).dispose();
      }),
    [lines],
  );

  return (
    <group>
      {lines.map((l) => (
        <primitive key={l.uuid} object={l} />
      ))}
    </group>
  );
}
