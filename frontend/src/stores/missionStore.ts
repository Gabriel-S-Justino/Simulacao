import { create } from "zustand";
import type { DesignIn, HohmannPlan, Simulation } from "../types/contracts";
import { toTrack, type Track } from "../rendering/playback";

export type Phase = "assembly" | "planning" | "operations";

export interface PartState {
  quantity: number;
  propellant_kg?: number;
}

export const DEFAULT_PARTS: Record<string, PartState> = {
  "core-s": { quantity: 1 },
  "obc-1": { quantity: 1 },
  "sa-600": { quantity: 2 },
  "bat-1kwh": { quantity: 1 },
  "ant-hga-1m": { quantity: 1 },
  "tx-x-20": { quantity: 1 },
  "rw-set-4": { quantity: 1 },
  "st-1": { quantity: 1 },
  "thermal-ctl": { quantity: 1 },
  "cam-ms-25": { quantity: 1 },
  "eng-biprop-400": { quantity: 1 },
  "tank-biprop-150": { quantity: 1 },
};

export interface PlanParams {
  initialAltitudeKm: number;
  targetAltitudeKm: number;
  inclinationDeg: number;
}

interface MissionState {
  phase: Phase;
  panelOpen: boolean;
  cleanMode: boolean;
  advancedOpen: boolean;
  parts: Record<string, PartState>;
  plan: PlanParams;
  hohmann: HohmannPlan | null;
  simulation: Simulation | null;
  track: Track | null;
  epochMs: number;
  playing: boolean;
  timeScale: number;
  setPhase: (p: Phase) => void;
  togglePanel: () => void;
  toggleClean: () => void;
  toggleAdvanced: () => void;
  setQuantity: (id: string, quantity: number) => void;
  setPropellant: (id: string, kg: number) => void;
  setPlan: (patch: Partial<PlanParams>) => void;
  setHohmann: (h: HohmannPlan | null) => void;
  loadSimulation: (s: Simulation) => void;
  setPlaying: (p: boolean) => void;
  setTimeScale: (s: number) => void;
}

export const useMission = create<MissionState>((set) => ({
  phase: "assembly",
  panelOpen: true,
  cleanMode: false,
  advancedOpen: false,
  parts: DEFAULT_PARTS,
  plan: { initialAltitudeKm: 400, targetAltitudeKm: 2000, inclinationDeg: 51.6 },
  hohmann: null,
  simulation: null,
  track: null,
  epochMs: Date.now(),
  playing: false,
  timeScale: 100,
  setPhase: (phase) => set({ phase, panelOpen: true }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  toggleClean: () => set((s) => ({ cleanMode: !s.cleanMode })),
  toggleAdvanced: () => set((s) => ({ advancedOpen: !s.advancedOpen })),
  setQuantity: (id, quantity) =>
    set((s) => {
      const parts = { ...s.parts };
      if (quantity <= 0) delete parts[id];
      else parts[id] = { ...parts[id], quantity: Math.min(quantity, 32) };
      return { parts, hohmann: null };
    }),
  setPropellant: (id, kg) =>
    set((s) => {
      const current = s.parts[id];
      if (!current) return s;
      return { parts: { ...s.parts, [id]: { ...current, propellant_kg: kg } }, hohmann: null };
    }),
  setPlan: (patch) => set((s) => ({ plan: { ...s.plan, ...patch }, hohmann: null })),
  setHohmann: (hohmann) => set({ hohmann }),
  loadSimulation: (simulation) => {
    playbackClock.t = 0;
    set({ simulation, track: toTrack(simulation), epochMs: Date.now(), playing: true, phase: "operations" });
  },
  setPlaying: (playing) => set({ playing }),
  setTimeScale: (timeScale) => set({ timeScale }),
}));

/**
 * Tempo de reprodução (s desde o início da missão). Mutável e fora do React:
 * avança a cada quadro sem provocar renderizações da interface.
 */
export const playbackClock = { t: 0 };

export function designFromParts(parts: Record<string, PartState>): DesignIn {
  return {
    stages: [
      {
        name: "Satélite",
        parts: Object.entries(parts).map(([component_id, p]) => ({
          component_id,
          quantity: p.quantity,
          ...(p.propellant_kg !== undefined ? { propellant_kg: p.propellant_kg } : {}),
        })),
      },
    ],
  };
}
