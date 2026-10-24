import type { z } from "zod";
import {
  CatalogSchema,
  DesignReportSchema,
  HohmannSchema,
  SimulationSchema,
  type DesignIn,
  type SimulateIn,
} from "../types/contracts";

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
};
