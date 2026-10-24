/**
 * Contratos com o backend (/api/v1). Toda resposta é validada com Zod antes de
 * entrar no estado da aplicação. Unidades SI, como no backend.
 */
import { z } from "zod";

export const ComponentSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.enum([
    "structure",
    "avionics",
    "propulsion_engine",
    "propulsion_tank",
    "power_solar",
    "power_battery",
    "comms",
    "attitude",
    "payload",
    "thermal",
  ]),
  mass_kg: z.number(),
  dimensions_m: z.tuple([z.number(), z.number(), z.number()]),
  power_consumption_w: z.number(),
  power_generation_w: z.number(),
  cost_musd: z.number(),
  reliability: z.number(),
  fictional: z.boolean(),
  source: z.string(),
  params: z.record(z.string(), z.unknown()),
});
export type Component = z.infer<typeof ComponentSchema>;
export type Category = Component["category"];

export const CatalogSchema = z.object({
  version: z.string(),
  notice: z.string(),
  components: z.array(ComponentSchema),
});
export type Catalog = z.infer<typeof CatalogSchema>;

export interface PartIn {
  component_id: string;
  quantity: number;
  propellant_kg?: number | null;
}
export interface StageIn {
  name: string;
  parts: PartIn[];
}
export interface DesignIn {
  stages: StageIn[];
}

const IssueSchema = z.object({
  severity: z.enum(["error", "warning"]),
  code: z.string(),
  message: z.string(),
  stage: z.number().nullable(),
});
export type Issue = z.infer<typeof IssueSchema>;

export const DesignReportSchema = z.object({
  valid: z.boolean(),
  stages: z.array(
    z.object({
      name: z.string(),
      dry_mass_kg: z.number(),
      propellant_kg: z.number(),
      thrust_n: z.number(),
      isp_s: z.number().nullable(),
      delta_v_ms: z.number(),
      burn_time_s: z.number().nullable(),
      initial_mass_kg: z.number(),
      final_mass_kg: z.number(),
    }),
  ),
  dry_mass_kg: z.number(),
  propellant_kg: z.number(),
  wet_mass_kg: z.number(),
  final_mass_kg: z.number(),
  total_delta_v_ms: z.number(),
  power_generation_w: z.number(),
  power_consumption_w: z.number(),
  power_margin_w: z.number(),
  battery_capacity_wh: z.number(),
  cost_musd: z.number(),
  reliability: z.number(),
  contains_fictional: z.boolean(),
  issues: z.array(IssueSchema),
});
export type DesignReport = z.infer<typeof DesignReportSchema>;

const ProvenanceSchema = z.object({
  source: z.string(),
  kind: z.enum(["calculated", "observed", "approximation", "synthetic"]),
  computed_at: z.string(),
  simulator_version: z.string(),
  model: z.string(),
  reference_frame: z.string(),
  units: z.record(z.string(), z.string()),
  assumptions: z.array(z.string()),
});
export type Provenance = z.infer<typeof ProvenanceSchema>;

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

export const BurnSchema = z.object({
  t_s: z.number(),
  dv_vnb_ms: Vec3,
  label: z.string(),
});
export type Burn = z.infer<typeof BurnSchema>;

export const HohmannSchema = z.object({
  dv1_ms: z.number(),
  dv2_ms: z.number(),
  total_delta_v_ms: z.number(),
  transfer_time_s: z.number(),
  transfer_semi_major_axis_m: z.number(),
  burns: z.array(BurnSchema),
  suggested_duration_s: z.number(),
  feasibility: z
    .object({
      available_delta_v_ms: z.number(),
      required_delta_v_ms: z.number(),
      margin_ms: z.number(),
      feasible: z.boolean(),
    })
    .nullable(),
  provenance: ProvenanceSchema,
});
export type HohmannPlan = z.infer<typeof HohmannSchema>;

const OrbitSchema = z.object({
  orbit_type: z.string(),
  semi_major_axis_m: z.number(),
  eccentricity: z.number(),
  inclination_deg: z.number(),
  periapsis_altitude_m: z.number(),
  apoapsis_altitude_m: z.number().nullable(),
  period_s: z.number().nullable(),
  specific_energy_jkg: z.number(),
  specific_angular_momentum_m2s: z.number(),
});
export type Orbit = z.infer<typeof OrbitSchema>;

export const SimEventSchema = z.object({
  t_s: z.number(),
  kind: z.string(),
  message: z.string(),
  data: z.record(z.string(), z.number()),
});
export type SimEvent = z.infer<typeof SimEventSchema>;

export const SimulationSchema = z.object({
  design: DesignReportSchema,
  initial_orbit: OrbitSchema,
  final_orbit: OrbitSchema.nullable(),
  trajectory: z.object({
    t_s: z.array(z.number()),
    position_m: z.array(Vec3),
    velocity_ms: z.array(Vec3),
    mass_kg: z.array(z.number()),
  }),
  events: z.array(SimEventSchema),
  delta_v_executed_ms: z.number(),
  propellant_used_kg: z.number(),
  final_mass_kg: z.number(),
  terminated_early: z.boolean(),
  objective: z
    .object({
      achieved: z.boolean(),
      periapsis_error_m: z.number().nullable(),
      apoapsis_error_m: z.number().nullable(),
      tolerance_m: z.number(),
    })
    .nullable(),
  diagnostics: z.object({
    integrator: z.string(),
    rtol: z.number(),
    atol_position_m: z.number(),
    atol_velocity_ms: z.number(),
    function_evaluations: z.number(),
    max_rel_energy_drift: z.number(),
    max_rel_angular_momentum_drift: z.number(),
    compute_time_ms: z.number(),
  }),
  provenance: ProvenanceSchema,
});
export type Simulation = z.infer<typeof SimulationSchema>;

export interface SimulateIn {
  design: DesignIn;
  initial_orbit: { altitude_m: number; inclination_deg: number };
  burns: Burn[];
  duration_s: number;
  n_samples?: number;
  objective?: { kind: "circular_orbit"; target_altitude_m: number; tolerance_m: number };
}

// --- Persistência (missões e checkpoints) ---

export const HealthSchema = z.object({
  status: z.string(),
  version: z.string(),
  database: z.enum(["ok", "unavailable", "not_configured"]),
});

export const ProjectSchema = z.object({
  id: z.string(),
  name: z.string(),
  created_at: z.string(),
  mission_count: z.number(),
});

const PartSchema = z.object({
  component_id: z.string(),
  quantity: z.number(),
  propellant_kg: z.number().nullable().optional(),
});

export const MissionSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  name: z.string(),
  status: z.enum(["draft", "simulated"]),
  design: z.object({ stages: z.array(z.object({ name: z.string(), parts: z.array(PartSchema) })) }),
  initial_orbit: z.object({ altitude_m: z.number(), inclination_deg: z.number() }),
  objective: z
    .object({ kind: z.literal("circular_orbit"), target_altitude_m: z.number(), tolerance_m: z.number() })
    .nullable(),
  burns: z.array(BurnSchema),
  duration_s: z.number(),
  seed: z.number(),
  simulator_version: z.string(),
  updated_at: z.string(),
  checkpoint_count: z.number(),
  run_count: z.number(),
});
export type Mission = z.infer<typeof MissionSchema>;

export const CheckpointSchema = z.object({
  id: z.string(),
  mission_id: z.string(),
  label: z.string(),
  t_s: z.number(),
  state: z.object({ t_s: z.number(), mass_kg: z.number() }),
  simulator_version: z.string(),
  created_at: z.string(),
});
export type Checkpoint = z.infer<typeof CheckpointSchema>;

export const MissionRunSchema = z.object({
  run_id: z.string(),
  from_checkpoint_id: z.string().nullable(),
  simulation: SimulationSchema,
});
export type MissionRun = z.infer<typeof MissionRunSchema>;

export interface MissionIn {
  project_id: string;
  name: string;
  design: DesignIn;
  initial_orbit: { altitude_m: number; inclination_deg: number };
  objective: { kind: "circular_orbit"; target_altitude_m: number; tolerance_m: number };
}
