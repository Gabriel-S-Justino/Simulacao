import { Metric } from "../../components/Metric";
import { useMission } from "../../stores/missionStore";
import { duration, fmt } from "../../utils/format";
import { useTelemetry } from "./useTelemetry";

/** Indicadores essenciais de voo (3 a 4), adaptados à atividade atual. */
export function FlightHud() {
  const sim = useMission((s) => s.simulation);
  const tel = useTelemetry();
  if (!sim) return null;
  const initialProp = sim.design.propellant_kg;
  const used = sim.design.wet_mass_kg - tel.massKg;
  const next = sim.events.find((e) => e.t_s > tel.t && e.kind === "burn");
  return (
    <div className="hud" aria-label="Telemetria">
      <Metric label="Altitude" value={fmt(tel.altitudeM / 1000, 1)} unit="km" />
      <Metric label="Velocidade" value={fmt(tel.speedMs / 1000, 3)} unit="km/s" />
      <Metric
        label="Propelente"
        value={fmt(Math.max(0, initialProp - used), 1)}
        unit="kg"
        tone={initialProp - used < 1 ? "error" : "default"}
      />
      {next && <Metric label="Próxima queima" value={`T−${duration(next.t_s - tel.t)}`} tone="accent" />}
    </div>
  );
}
