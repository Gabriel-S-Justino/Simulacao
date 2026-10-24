import { z } from "zod";
import {
  CatalogSchema,
  CheckpointSchema,
  HealthSchema,
  MissionRunSchema,
  MissionSchema,
  ProjectSchema,
  type MissionIn,
  DesignReportSchema,
  HohmannSchema,
  SimulationSchema,
  type DesignIn,
  type SimulateIn,
} from "../types/contracts";
import {
  EarthEventsEnvelopeSchema,
  GibsCatalogSchema,
  IssEnvelopeSchema,
  SpaceWeatherSchema,
} from "../types/sources";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<S extends z.ZodType>(
  schema: S,
  path: string,
  init?: RequestInit,
): Promise<z.infer<S>> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("Servidor indisponível.", 0);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body && typeof body.detail === "string"
        ? body.detail
        : `Erro ${res.status}`;
    throw new ApiError(detail, res.status);
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError("Resposta inválida do servidor.", res.status);
  return parsed.data;
}

const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
  signal: signal ?? null,
});

export const api = {
  catalog: () => request(CatalogSchema, "/api/v1/catalog/components"),
  evaluate: (design: DesignIn, signal?: AbortSignal) =>
    request(DesignReportSchema, "/api/v1/spacecraft/evaluate", post(design, signal)),
  hohmann: (
    body: { initial_altitude_m: number; target_altitude_m: number; design: DesignIn },
    signal?: AbortSignal,
  ) => request(HohmannSchema, "/api/v1/planning/hohmann", post(body, signal)),
  simulate: (body: SimulateIn) =>
    request(SimulationSchema, "/api/v1/simulations/propagate", post(body)),

  health: () => request(HealthSchema, "/api/v1/health"),
  projects: () => request(z.array(ProjectSchema), "/api/v1/projects"),
  createProject: (name: string) => request(ProjectSchema, "/api/v1/projects", post({ name })),
  missions: () => request(z.array(MissionSchema), "/api/v1/missions"),
  createMission: (body: MissionIn) => request(MissionSchema, "/api/v1/missions", post(body)),
  deleteMission: (id: string) =>
    fetch(`${BASE}/api/v1/missions/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new ApiError(`Erro ${r.status}`, r.status);
    }),
  planMission: (id: string) => request(MissionSchema, `/api/v1/missions/${id}/plan`, post({})),
  runMission: (id: string, n_samples = 2000) =>
    request(MissionRunSchema, `/api/v1/missions/${id}/run`, post({ n_samples })),
  checkpoints: (id: string) =>
    request(z.array(CheckpointSchema), `/api/v1/missions/${id}/checkpoints`),
  createCheckpoint: (id: string, t_s: number, label: string) =>
    request(CheckpointSchema, `/api/v1/missions/${id}/checkpoints`, post({ t_s, label })),
  resume: (id: string, checkpointId: string, n_samples = 2000) =>
    request(
      MissionRunSchema,
      `/api/v1/missions/${id}/checkpoints/${checkpointId}/resume`,
      post({ n_samples }),
    ),

  // Fontes externas: o backend sempre responde com o envelope §4.9.
  issPosition: () => request(IssEnvelopeSchema, "/api/v1/iss/position"),
  earthEvents: (days = 30, limit = 200) =>
    request(EarthEventsEnvelopeSchema, `/api/v1/events/earth?days=${days}&limit=${limit}`),
  spaceWeather: (days = 7) => request(SpaceWeatherSchema, `/api/v1/events/space-weather?days=${days}`),
  gibsLayers: () => request(GibsCatalogSchema, "/api/v1/earth/imagery/layers"),
};
