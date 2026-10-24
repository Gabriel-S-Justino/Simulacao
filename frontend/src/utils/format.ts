const nf = (digits: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const fmt = (value: number, digits = 0) => nf(digits).format(value);

export const km = (m: number, digits = 0) => `${fmt(m / 1000, digits)} km`;
export const kms = (ms: number, digits = 2) => `${fmt(ms / 1000, digits)} km/s`;
export const ms = (v: number, digits = 0) => `${fmt(v, digits)} m/s`;
export const kg = (v: number, digits = 1) => `${fmt(v, digits)} kg`;
export const watts = (w: number) => (Math.abs(w) >= 1000 ? `${fmt(w / 1000, 2)} kW` : `${fmt(w)} W`);

export function duration(s: number): string {
  const sign = s < 0 ? "−" : "";
  let x = Math.abs(Math.round(s));
  const d = Math.floor(x / 86_400);
  x -= d * 86_400;
  const h = Math.floor(x / 3600);
  x -= h * 3600;
  const m = Math.floor(x / 60);
  const sec = x - m * 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${sign}${d > 0 ? `${d}d ` : ""}${pad(h)}:${pad(m)}:${pad(sec)}`;
}
