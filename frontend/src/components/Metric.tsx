export type Tone = "default" | "ok" | "error" | "accent";

export function Metric({
  label,
  value,
  unit,
  tone = "default",
  title,
}: {
  label: string;
  value: string;
  unit?: string;
  tone?: Tone;
  title?: string;
}) {
  return (
    <div className="metric" data-tone={tone} title={title}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">
        {value}
        {unit && <small>{unit}</small>}
      </div>
    </div>
  );
}
