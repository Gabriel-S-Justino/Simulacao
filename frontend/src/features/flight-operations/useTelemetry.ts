import { useEffect, useState } from "react";
import { craftPosition } from "../../rendering/craftPosition";
import { playbackClock } from "../../stores/missionStore";

export interface Telemetry {
  t: number;
  altitudeM: number;
  speedMs: number;
  massKg: number;
}

/** Amostra a telemetria visual a 10 Hz: a interface não renderiza a cada quadro. */
export function useTelemetry(hz = 10): Telemetry {
  const [tel, setTel] = useState<Telemetry>(read);
  useEffect(() => {
    const id = setInterval(() => setTel(read()), 1000 / hz);
    return () => clearInterval(id);
  }, [hz]);
  return tel;
}

function read(): Telemetry {
  const { r, v, mass } = craftPosition.state;
  return {
    t: playbackClock.t,
    altitudeM: Math.hypot(r[0], r[1], r[2]) - 6_378_137,
    speedMs: Math.hypot(v[0], v[1], v[2]),
    massKg: mass,
  };
}
