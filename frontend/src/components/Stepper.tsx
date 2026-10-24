export function Stepper({
  value,
  onChange,
  label,
  max = 32,
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
  max?: number;
}) {
  return (
    <span className="stepper" role="group" aria-label={label}>
      <button aria-label={`Remover ${label}`} disabled={value <= 0} onClick={() => onChange(value - 1)}>
        −
      </button>
      <span>{value}</span>
      <button aria-label={`Adicionar ${label}`} disabled={value >= max} onClick={() => onChange(value + 1)}>
        +
      </button>
    </span>
  );
}
