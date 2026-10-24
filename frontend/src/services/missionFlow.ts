import { api } from "./api";
import type { DesignIn, MissionRun } from "../types/contracts";
import type { PlanParams } from "../stores/missionStore";

export const OBJECTIVE_TOLERANCE_M = 1000;
const DEFAULT_PROJECT = "Minha agência";

async function projectId(): Promise<string> {
  const projects = await api.projects();
  return projects[0]?.id ?? (await api.createProject(DEFAULT_PROJECT)).id;
}

/**
 * Salva a configuração atual como missão (se ainda não salva), planeja no backend e executa.
 * O plano gravado é o mesmo Hohmann exibido na interface, calculado pelo servidor.
 */
export async function saveAndRun(
  design: DesignIn,
  plan: PlanParams,
  missionId: string | null,
): Promise<{ missionId: string; run: MissionRun }> {
  let id = missionId;
  if (id === null) {
    const created = await api.createMission({
      project_id: await projectId(),
      name: `Órbita de ${plan.targetAltitudeKm} km`,
      design,
      initial_orbit: { altitude_m: plan.initialAltitudeKm * 1000, inclination_deg: plan.inclinationDeg },
      objective: {
        kind: "circular_orbit",
        target_altitude_m: plan.targetAltitudeKm * 1000,
        tolerance_m: OBJECTIVE_TOLERANCE_M,
      },
    });
    await api.planMission(created.id);
    id = created.id;
  }
  return { missionId: id, run: await api.runMission(id) };
}
