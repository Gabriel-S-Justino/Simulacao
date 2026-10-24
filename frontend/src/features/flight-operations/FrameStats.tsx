import { useEffect, useState } from "react";
import { frameStats } from "../../rendering/scene/frameStats";
import { useView } from "../../stores/viewStore";
import { fmt } from "../../utils/format";

/** Desempenho medido no dispositivo atual (últimos 600 quadros). */
export function FrameStats() {
  const [s, setS] = useState(frameStats);
  const dpr = useView((v) => v.dpr);
  useEffect(() => {
    const id = setInterval(() => setS(frameStats()), 500);
    return () => clearInterval(id);
  }, []);
  if (!s) return null;
  return (
    <>
      <dt>Quadros</dt>
      <dd>
        {fmt(s.fps, 0)} FPS · p95 {fmt(s.p95, 1)} ms · p99 {fmt(s.p99, 1)} ms
      </dd>
      <dt>Resolução</dt>
      <dd>DPR {fmt(dpr, 2)}</dd>
    </>
  );
}
