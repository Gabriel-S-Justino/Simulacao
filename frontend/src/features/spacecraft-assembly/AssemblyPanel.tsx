import { useMemo } from "react";
import { Metric } from "../../components/Metric";
import { Stepper } from "../../components/Stepper";
import { useCatalog, useDesignReport } from "../../services/queries";
import { designFromParts, useMission } from "../../stores/missionStore";
import type { Category, Component } from "../../types/contracts";
import { fmt, watts } from "../../utils/format";

const GROUPS: { title: string; categories: Category[] }[] = [
  { title: "Propulsão", categories: ["propulsion_engine", "propulsion_tank"] },
  { title: "Energia", categories: ["power_solar", "power_battery"] },
  { title: "Comunicação", categories: ["comms"] },
  { title: "Carga científica", categories: ["payload"] },
  { title: "Atitude", categories: ["attitude"] },
  { title: "Estrutura e sistemas", categories: ["structure", "avionics", "thermal"] },
];

export function AssemblyPanel() {
  const parts = useMission((s) => s.parts);
  const setQuantity = useMission((s) => s.setQuantity);
  const setPropellant = useMission((s) => s.setPropellant);
  const setPhase = useMission((s) => s.setPhase);
  const catalog = useCatalog();
  const design = useMemo(() => designFromParts(parts), [parts]);
  const report = useDesignReport(design);
  const r = report.data;

  const grouped = useMemo(() => {
    const comps = catalog.data?.components ?? [];
    return GROUPS.map((g) => ({
      ...g,
      items: comps.filter((c) => g.categories.includes(c.category) && !c.params.separator),
    }));
  }, [catalog.data]);

  if (catalog.isError) return <p className="note">Catálogo indisponível: {catalog.error.message}</p>;

  const errors = r?.issues.filter((i) => i.severity === "error") ?? [];
  const tanks = (catalog.data?.components ?? []).filter(
    (c) => c.category === "propulsion_tank" && parts[c.id],
  );

  return (
    <>
      <div className="metrics" aria-live="polite">
        <Metric label="Delta-v" value={r ? fmt(r.total_delta_v_ms) : "—"} unit="m/s" tone="accent" />
        <Metric label="Massa inicial" value={r ? fmt(r.wet_mass_kg, 1) : "—"} unit="kg" />
        <Metric
          label="Margem de energia"
          value={r ? watts(r.power_margin_w) : "—"}
          tone={r && r.power_margin_w < 0 ? "error" : "default"}
          title={r ? `Geração ${watts(r.power_generation_w)} · Consumo ${watts(r.power_consumption_w)}` : undefined}
        />
        <Metric label="Custo" value={r ? fmt(r.cost_musd, 1) : "—"} unit="M$" />
      </div>

      {report.isError && <p className="note">Avaliação indisponível: {report.error.message}</p>}
      {r && r.issues.length > 0 && (
        <ul className="issues">
          {r.issues.map((i) => (
            <li key={i.code + (i.stage ?? "")} className="issue" data-severity={i.severity}>
              {i.message}
            </li>
          ))}
        </ul>
      )}

      {tanks.map((t) => (
        <PropellantSlider
          key={t.id}
          tank={t}
          value={parts[t.id]?.propellant_kg ?? Number(t.params.capacity_kg)}
          onChange={(kg) => setPropellant(t.id, kg)}
        />
      ))}

      {grouped.map((g) => (
        <div className="section" key={g.title}>
          <div className="section-title">{g.title}</div>
          {g.items.map((c) => {
            const q = parts[c.id]?.quantity ?? 0;
            return (
              <div className="part" key={c.id} data-qty={q} title={partTooltip(c)}>
                <span className="part-name">{c.name}</span>
                <span className="part-mass">{fmt(c.mass_kg, 1)} kg</span>
                <Stepper label={c.name} value={q} onChange={(v) => setQuantity(c.id, v)} />
              </div>
            );
          })}
        </div>
      ))}

      <button className="primary" disabled={!r || errors.length > 0} onClick={() => setPhase("planning")}>
        Planejar missão
      </button>
      {catalog.data && <p className="note">{catalog.data.notice}</p>}
    </>
  );
}

function PropellantSlider({
  tank,
  value,
  onChange,
}: {
  tank: Component;
  value: number;
  onChange: (kg: number) => void;
}) {
  const cap = Number(tank.params.capacity_kg);
  return (
    <div className="section">
      <div className="field">
        <label htmlFor={`prop-${tank.id}`}>Propelente</label>
        <span className="mono">
          {fmt(value, 0)} / {fmt(cap, 0)} kg
        </span>
      </div>
      <input
        id={`prop-${tank.id}`}
        className="slider"
        type="range"
        min={0}
        max={cap}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function partTooltip(c: Component): string {
  const lines = [`${c.name} (fictício)`, `Massa ${fmt(c.mass_kg, 1)} kg`];
  if (c.power_consumption_w) lines.push(`Consumo ${watts(c.power_consumption_w)}`);
  if (c.power_generation_w) lines.push(`Geração ${watts(c.power_generation_w)} a 1 UA`);
  if (c.params.thrust_n !== undefined) lines.push(`Empuxo ${c.params.thrust_n} N · Isp ${c.params.isp_s} s`);
  if (c.params.capacity_kg !== undefined) lines.push(`Capacidade ${c.params.capacity_kg} kg`);
  return lines.join("\n");
}
