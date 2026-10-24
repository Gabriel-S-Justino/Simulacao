import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Metric } from "../../components/Metric";
import { api } from "../../services/api";
import { OBJECTIVE_TOLERANCE_M, saveAndRun } from "../../services/missionFlow";
import { useHohmann, usePersistence } from "../../services/queries";
import { SavedMissions } from "./SavedMissions";
import { designFromParts, useMission } from "../../stores/missionStore";
import { duration, fmt } from "../../utils/format";

export function PlanPanel() {
  const parts = useMission((s) => s.parts);
  const plan = useMission((s) => s.plan);
  const setPlan = useMission((s) => s.setPlan);
  const loadSimulation = useMission((s) => s.loadSimulation);
  const missionId = useMission((s) => s.missionId);
  const setMissionId = useMission((s) => s.setMissionId);
  const persistence = usePersistence();
  const queryClient = useQueryClient();
  const design = useMemo(() => designFromParts(parts), [parts]);
  const hohmann = useHohmann(plan.initialAltitudeKm, plan.targetAltitudeKm, design);
  const h = hohmann.data;
  const f = h?.feasibility;

  const simulate = useMutation({
    mutationFn: async () => {
      if (!h) throw new Error("Plano indisponível.");
      if (persistence) {
        const { missionId: id, run } = await saveAndRun(design, plan, missionId);
        return { simulation: run.simulation, missionId: id };
      }
      const simulation = await api.simulate({
        design,
        initial_orbit: { altitude_m: plan.initialAltitudeKm * 1000, inclination_deg: plan.inclinationDeg },
        burns: h.burns,
        duration_s: h.suggested_duration_s,
        n_samples: 2000,
        objective: {
          kind: "circular_orbit",
          target_altitude_m: plan.targetAltitudeKm * 1000,
          tolerance_m: OBJECTIVE_TOLERANCE_M,
        },
      });
      return { simulation, missionId: null };
    },
    onSuccess: ({ simulation, missionId: id }) => {
      loadSimulation(simulation);
      setMissionId(id);
      void queryClient.invalidateQueries({ queryKey: ["missions"] });
    },
  });

  return (
    <>
      <div className="section-title" style={{ marginTop: 6 }}>
        Objetivo: órbita circular
      </div>
      <NumberField
        label="Altitude inicial"
        unit="km"
        value={plan.initialAltitudeKm}
        min={150}
        max={400_000}
        onChange={(v) => setPlan({ initialAltitudeKm: v })}
      />
      <NumberField
        label="Altitude alvo"
        unit="km"
        value={plan.targetAltitudeKm}
        min={150}
        max={400_000}
        onChange={(v) => setPlan({ targetAltitudeKm: v })}
      />
      <NumberField
        label="Inclinação"
        unit="°"
        value={plan.inclinationDeg}
        min={0}
        max={180}
        onChange={(v) => setPlan({ inclinationDeg: v })}
      />

      <div className="metrics" style={{ borderTop: "1px solid var(--line)", marginTop: 10, paddingTop: 14 }}>
        <Metric label="Delta-v necessário" value={h ? fmt(h.total_delta_v_ms) : "—"} unit="m/s" tone="accent" />
        <Metric
          label="Disponível"
          value={f ? fmt(f.available_delta_v_ms) : "—"}
          unit="m/s"
          tone={f ? (f.feasible ? "ok" : "error") : "default"}
        />
        <Metric label="Transferência" value={h ? duration(h.transfer_time_s) : "—"} />
        <Metric
          label="Margem"
          value={f ? fmt(f.margin_ms) : "—"}
          unit="m/s"
          tone={f && f.margin_ms < 0 ? "error" : "default"}
        />
      </div>

      {hohmann.isError && <p className="note">{hohmann.error.message}</p>}
      {f && !f.feasible && (
        <ul className="issues">
          <li className="issue" data-severity="error">
            Faltam {fmt(-f.margin_ms)} m/s de delta-v. Aumente o propelente ou reduza a massa.
          </li>
        </ul>
      )}

      <button
        className="primary"
        data-tone={f && !f.feasible ? "warn" : undefined}
        disabled={!h || simulate.isPending}
        onClick={() => simulate.mutate()}
      >
        {simulate.isPending ? "Simulando…" : f && !f.feasible ? "Simular mesmo assim" : "Lançar simulação"}
      </button>
      {simulate.isError && <p className="note" style={{ color: "var(--error)" }}>{simulate.error.message}</p>}
      <p className="note">
        {persistence
          ? missionId
            ? "Missão salva. A simulação usa o plano gravado."
            : "A missão será salva ao simular."
          : "Banco indisponível: a simulação não será salva."}
      </p>
      {persistence && <SavedMissions />}
      {h && (
        <p className="note">
          Transferência de Hohmann: {h.provenance.assumptions.join(" · ").toLowerCase()}.
        </p>
      )}
    </>
  );
}

function NumberField({
  label,
  unit,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const id = `f-${label}`;
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const n = Number(draft);
  const valid = draft.trim() !== "" && Number.isFinite(n) && n >= min && n <= max;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <span>
        <input
          id={id}
          type="number"
          value={draft}
          min={min}
          max={max}
          aria-invalid={!valid}
          style={valid ? undefined : { borderColor: "var(--error)" }}
          onChange={(e) => {
            setDraft(e.target.value);
            const v = Number(e.target.value);
            if (e.target.value.trim() !== "" && Number.isFinite(v) && v >= min && v <= max) onChange(v);
          }}
          onBlur={() => setDraft(String(value))}
        />{" "}
        <span className="metric-label">{unit}</span>
      </span>
    </div>
  );
}
