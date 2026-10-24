/**
 * Contratos das fontes externas (envelope §4.9 do backend). O estado da fonte
 * vem em `status`; `data` é null quando a fonte falhou e não há cópia em cache.
 */
import { z } from "zod";

const SourceErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  retryable: z.boolean(),
  http_status: z.number().nullable().optional(),
});

export const envelope = <T extends z.ZodType>(data: T) =>
  z.object({
    source: z.string(),
    status: z.enum(["ok", "stale", "error", "not_configured"]),
    fetched_at: z.string().nullable(),
    observed_at: z.string().nullable(),
    valid_time_start: z.string().nullable(),
    valid_time_end: z.string().nullable(),
    stale: z.boolean(),
    units: z.record(z.string(), z.string()),
    reference_frame: z.string().nullable(),
    uncertainty: z.string().nullable(),
    data: data.nullable(),
    error: SourceErrorSchema.nullable(),
    notes: z.array(z.string()),
    attribution: z.string().nullable(),
  });

export interface Envelope<T> {
  source: string;
  status: "ok" | "stale" | "error" | "not_configured";
  fetched_at: string | null;
  observed_at: string | null;
  stale: boolean;
  data: T | null;
  error: z.infer<typeof SourceErrorSchema> | null;
  notes: string[];
  attribution: string | null;
  reference_frame: string | null;
  uncertainty: string | null;
}

export const IssPositionSchema = z.object({
  lat_deg: z.number(),
  lon_deg: z.number(),
  observed_at: z.string(),
});
export const IssEnvelopeSchema = envelope(IssPositionSchema);

export const EarthEventSchema = z.object({
  id: z.string(),
  title: z.string(),
  link: z.string().nullable(),
  closed: z.string().nullable(),
  categories: z.array(z.object({ id: z.string(), title: z.string() })),
  geometry: z.array(
    z.object({
      date: z.string(),
      kind: z.enum(["point", "polygon"]),
      lon_deg: z.number(),
      lat_deg: z.number(),
      point_method: z.enum(["point", "polygon_vertex_mean"]),
      magnitude_value: z.number().nullable(),
      magnitude_unit: z.string().nullable(),
    }),
  ),
});
export type EarthEvent = z.infer<typeof EarthEventSchema>;
export const EarthEventsEnvelopeSchema = envelope(z.array(EarthEventSchema));

export const SpaceWeatherSchema = z.object({
  start: z.string(),
  end: z.string(),
  flares: envelope(
    z.array(
      z.object({
        id: z.string(),
        begin: z.string(),
        peak: z.string().nullable(),
        class_type: z.string().nullable(),
        source_location: z.string().nullable(),
      }),
    ),
  ),
  storms: envelope(z.array(z.object({ id: z.string(), start: z.string(), kp_max: z.number().nullable() }))),
  cmes: envelope(
    z.array(
      z.object({
        id: z.string(),
        start: z.string(),
        analysis: z
          .object({ speed_ms: z.number().nullable(), half_angle_deg: z.number().nullable() })
          .nullable(),
      }),
    ),
  ),
});
export type SpaceWeather = z.infer<typeof SpaceWeatherSchema>;

export const GibsCatalogSchema = envelope(
  z.object({
    wms_endpoint: z.string(),
    layers: z.array(
      z.object({ id: z.string(), title: z.string(), latest_date: z.string().nullable() }),
    ),
    missing: z.array(z.string()),
  }),
);
export type GibsCatalog = z.infer<typeof GibsCatalogSchema>;
