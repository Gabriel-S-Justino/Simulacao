import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { playbackClock } from "../../stores/missionStore";
import { sampleIndex, type Track } from "../playback";
import { METERS_PER_UNIT } from "../frames";

function buildGeometry(track: Track): THREE.BufferGeometry {
  const n = track.t.length;
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    pos[i * 3] = track.r[i * 3]! / METERS_PER_UNIT;
    pos[i * 3 + 1] = track.r[i * 3 + 2]! / METERS_PER_UNIT;
    pos[i * 3 + 2] = -track.r[i * 3 + 1]! / METERS_PER_UNIT;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.computeBoundingSphere();
  return g;
}

/** Trajetória calculada: completa (tênue) e percorrida (destacada). Mesma geometria, sem cópias. */
export function OrbitPath({ track }: { track: Track }) {
  const geometry = useMemo(() => buildGeometry(track), [track]);
  const lines = useMemo(() => {
    const traveled = new THREE.BufferGeometry();
    traveled.setAttribute("position", geometry.getAttribute("position"));
    traveled.boundingSphere = geometry.boundingSphere;
    const full = new THREE.Line(
      geometry,
      new THREE.LineBasicMaterial({ color: "#7fa7d9", transparent: true, opacity: 0.22, depthWrite: false }),
    );
    const done = new THREE.Line(
      traveled,
      new THREE.LineBasicMaterial({ color: "#e8f1ff", transparent: true, opacity: 0.85, depthWrite: false }),
    );
    return { full, done, traveled };
  }, [geometry]);

  useEffect(
    () => () => {
      geometry.dispose();
      lines.traveled.dispose();
      (lines.full.material as THREE.Material).dispose();
      (lines.done.material as THREE.Material).dispose();
    },
    [geometry, lines],
  );

  useFrame(() => {
    lines.traveled.setDrawRange(0, sampleIndex(track.t, playbackClock.t) + 1);
  });

  return (
    <group>
      <primitive object={lines.full} />
      <primitive object={lines.done} />
    </group>
  );
}
