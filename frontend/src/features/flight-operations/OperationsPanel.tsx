import { playbackClock, useMission } from "../../stores/missionStore";
import { FrameStats } from "./FrameStats";
import { duration, fmt, km } from "../../utils/format";

export function OperationsPanel() {
  const sim = useMission((s) => s.simulation);
  const advanced = useMission((s) => s.advancedOpen);
  const toggleAdvanced = useMission((s) => s.toggleAdvanced);
  const setPhase = useMission((s) => s.setPhase);
  if (!sim) {
    return (
      <>
        <p className="note">Nenhuma simulação executada.</p>
        <button className="primary" onClick={() => setPhase("planning")}>
          Ir para o planejamento
        </button>
      </>
    );
  }
  const o = sim.objective;
  const fo = sim.final_orbit;
  const d = sim.diagnostics;

  return (
    <>
      {o && (
        <div className="result" data-ok={o.achieved}>
          <strong>{o.achieved ? "Órbita alvo atingida" : "Objetivo não atingido"}</strong>
          <span className="metric-label">
            {fo
              ? `Periapsis ${km(fo.periapsis_altitude_m, 1)} · Apoapsis ${
                  fo.apoapsis_altitude_m === null ? "—" : km(fo.apoapsis_altitude_m, 1)
                }`
              : "Trajetória interrompida"}
            {` · tolerância ±${km(o.tolerance_m, 1)}`}
          </span>
        </div>
      )}

      <dl className="kv" style={{ margin: "12px 0" }}>
        <dt>Delta-v executado</dt>
        <dd>{fmt(sim.delta_v_executed_ms, 1)} m/s</dd>
        <dt>Propelente usado</dt>
        <dd>{fmt(sim.propellant_used_kg, 2)} kg</dd>
        <dt>Massa final</dt>
        <dd>{fmt(sim.final_mass_kg, 2)} kg</dd>
        {fo && (
          <>
            <dt>Excentricidade</dt>
            <dd>{fo.eccentricity.toExponential(2)}</dd>
            <dt>Período</dt>
            <dd>{fo.period_s ? duration(fo.period_s) : "—"}</dd>
          </>
        )}
      </dl>

      <div className="section-title">Eventos</div>
      <ul className="events">
        {sim.events.map((e, i) => (
          <li key={i} data-kind={e.kind}>
            <button onClick={() => (playbackClock.t = Math.max(0, e.t_s - 60))}>
              <span className="t">T+{duration(e.t_s)}</span>
              <span>{e.message}</span>
            </button>
          </li>
        ))}
      </ul>

      <button className="link" onClick={toggleAdvanced} aria-expanded={advanced}>
        {advanced ? "Ocultar detalhes técnicos" : "Detalhes técnicos"}
      </button>
      {advanced && (
        <dl className="kv">
          <dt>Modelo</dt>
          <dd>{sim.provenance.model}</dd>
          <dt>Referencial</dt>
          <dd>{sim.provenance.reference_frame}</dd>
          <dt>Integrador</dt>
          <dd>{d.integrator}</dd>
          <dt>Tolerâncias</dt>
          <dd>
            rtol {d.rtol.toExponential(0)} · {d.atol_position_m.toExponential(0)} m
          </dd>
          <dt>Avaliações</dt>
          <dd>{fmt(d.function_evaluations)}</dd>
          <dt>Deriva de energia</dt>
          <dd>{d.max_rel_energy_drift.toExponential(2)}</dd>
          <dt>Deriva de h</dt>
          <dd>{d.max_rel_angular_momentum_drift.toExponential(2)}</dd>
          <dt>Cálculo</dt>
          <dd>{fmt(d.compute_time_ms, 0)} ms</dd>
          <dt>Hipóteses</dt>
          <dd>{sim.provenance.assumptions.join("; ")}</dd>
          <dt>Interpolação</dt>
          <dd>Hermite cúbica, somente visual</dd>
          <FrameStats />
        </dl>
      )}
    </>
  );
}
