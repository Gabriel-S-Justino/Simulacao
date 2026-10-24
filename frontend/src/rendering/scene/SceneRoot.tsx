import { PerformanceMonitor } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useState } from "react";
import * as THREE from "three";
import { playbackClock, useMission } from "../../stores/missionStore";
import { QUALITY_DPR, useView } from "../../stores/viewStore";
import { Earth } from "../celestial-bodies/Earth";
import { updateCraftPosition } from "../craftPosition";
import { sunDirectionEci } from "../frames";
import { OrbitPath } from "../orbits/OrbitPath";
import { PlannedOrbits } from "../orbits/PlannedOrbits";
import { Spacecraft } from "../spacecraft/Spacecraft";
import { CameraRig } from "./CameraRig";
import { recordFrame } from "./frameStats";
import { Starfield } from "./Starfield";
import { Sun } from "./Sun";

/** Avança o relógio de reprodução e atualiza estados visuais derivados, uma vez por quadro. */
function Ticker({ sunDir }: { sunDir: THREE.Vector3 }) {
  useFrame((_, dt) => {
    recordFrame(dt * 1000);
    const { playing, timeScale, track, epochMs } = useMission.getState();
    if (playing && track) {
      // dt limitado: uma aba em segundo plano não deve saltar a missão de uma vez.
      playbackClock.t = Math.min(playbackClock.t + Math.min(dt, 0.1) * timeScale, track.duration);
      if (playbackClock.t >= track.duration) useMission.getState().setPlaying(false);
    }
    const [x, y, z] = sunDirectionEci(new Date(epochMs + playbackClock.t * 1000));
    sunDir.set(x, z, -y).normalize();
    updateCraftPosition();
  }, -1);
  return null;
}

export function SceneRoot({ onContextLost }: { onContextLost: (lost: boolean) => void }) {
  const sunDir = useMemo(() => new THREE.Vector3(1, 0, 0), []);
  const track = useMission((s) => s.track);
  const phase = useMission((s) => s.phase);
  const { dpr, autoQuality, quality, setDpr } = useView();
  const [, setFlips] = useState(0);

  return (
    <Canvas
      dpr={dpr}
      camera={{ position: [0.02, 0.012, 0.03], fov: 45, near: 0.0005, far: 200_000 }}
      gl={{ antialias: true, logarithmicDepthBuffer: true, powerPreference: "high-performance" }}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.0;
        gl.outputColorSpace = THREE.SRGBColorSpace;
        const el = gl.domElement;
        el.addEventListener("webglcontextlost", (e) => {
          e.preventDefault();
          onContextLost(true);
        });
        el.addEventListener("webglcontextrestored", () => onContextLost(false));
      }}
    >
      <color attach="background" args={["#000000"]} />
      {autoQuality && (
        <PerformanceMonitor
          flipflops={3}
          onDecline={() => setDpr(Math.max(1, dpr - 0.25))}
          onIncline={() => setDpr(Math.min(QUALITY_DPR[quality], dpr + 0.25))}
          onFallback={() => {
            setDpr(1);
            setFlips((f) => f + 1);
          }}
        />
      )}
      <Ticker sunDir={sunDir} />
      <Sun direction={sunDir} />
      <Starfield />
      <Earth sunDir={sunDir} />
      {track ? <OrbitPath track={track} /> : phase === "planning" && <PlannedOrbits />}
      <Spacecraft sunDir={sunDir} />
      <CameraRig sunDir={sunDir} />
    </Canvas>
  );
}
