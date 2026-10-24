import { afterEach, describe, expect, it, vi } from "vitest";
import { saveAndRun } from "../services/missionFlow";

afterEach(() => vi.restoreAllMocks());

const mission = {
  id: "m1", project_id: "p1", name: "x", status: "draft",
  design: { stages: [] }, initial_orbit: { altitude_m: 4e5, inclination_deg: 0 },
  objective: null, burns: [], duration_s: 100, seed: 0, simulator_version: "0.1.0",
  updated_at: "2026-10-24T00:00:00Z", checkpoint_count: 0, run_count: 0,
};

describe("saveAndRun", () => {
  it("cria projeto e missão, planeja no backend e executa", async () => {
    const calls: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      const path = String(url);
      calls.push(`${init?.method ?? "GET"} ${path}`);
      if (path.endsWith("/projects") && !init?.method)
        return new Response("[]");
      if (path.endsWith("/projects"))
        return new Response(JSON.stringify({ id: "p1", name: "a", created_at: "t", mission_count: 0 }));
      if (path.endsWith("/missions") || path.endsWith("/plan"))
        return new Response(JSON.stringify(mission));
      return new Response(JSON.stringify({ run_id: "r", from_checkpoint_id: null, simulation: {} }));
    });
    await expect(
      saveAndRun({ stages: [] }, { initialAltitudeKm: 400, targetAltitudeKm: 800, inclinationDeg: 0 }, null),
    ).rejects.toThrow("Resposta inválida");
    expect(calls).toEqual([
      "GET /api/v1/projects",
      "POST /api/v1/projects",
      "POST /api/v1/missions",
      "POST /api/v1/missions/m1/plan",
      "POST /api/v1/missions/m1/run",
    ]);
  });

  it("missão já salva: apenas executa", async () => {
    const calls: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      calls.push(`${init?.method ?? "GET"} ${String(url)}`);
      return new Response("{}");
    });
    await saveAndRun({ stages: [] }, { initialAltitudeKm: 400, targetAltitudeKm: 800, inclinationDeg: 0 }, "m9").catch(
      () => undefined,
    );
    expect(calls).toEqual(["POST /api/v1/missions/m9/run"]);
  });
});
