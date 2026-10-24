import * as THREE from "three";
import { useMission, playbackClock } from "../stores/missionStore";
import { EARTH_RADIUS_M, METERS_PER_UNIT } from "./frames";
import { newState, stateAt } from "./playback";

/**
 * Posição visual da nave, recalculada uma vez por quadro (ver CraftTracker) e
 * lida pela nave, pela câmera e pelo HUD. Somente apresentação.
 */
export const craftPosition = {
  state: newState(),
  scene: new THREE.Vector3(),
};

export function updateCraftPosition(): void {
  const { track, plan } = useMission.getState();
  const st = craftPosition.state;
  if (track) {
    stateAt(track, playbackClock.t, st);
  } else {
    // Sem simulação: nave exibida em repouso no ponto inicial da órbita planejada.
    const r = EARTH_RADIUS_M + plan.initialAltitudeKm * 1000;
    const inc = (plan.inclinationDeg * Math.PI) / 180;
    st.r[0] = r;
    st.r[1] = 0;
    st.r[2] = 0;
    st.v[0] = 0;
    st.v[1] = Math.cos(inc);
    st.v[2] = Math.sin(inc);
  }
  craftPosition.scene.set(st.r[0] / METERS_PER_UNIT, st.r[2] / METERS_PER_UNIT, -st.r[1] / METERS_PER_UNIT);
}
