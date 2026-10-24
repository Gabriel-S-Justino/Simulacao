/**
 * Reprodução visual de uma trajetória calculada pelo backend.
 *
 * A interpolação (Hermite cúbica com posição e velocidade das amostras) serve
 * somente à apresentação: os valores físicos de referência são as amostras do
 * núcleo científico. Nada aqui retroalimenta a simulação.
 */
import type { Simulation } from "../types/contracts";

export interface Track {
  t: Float64Array;
  r: Float64Array; // xyz intercalado, m
  v: Float64Array; // xyz intercalado, m/s
  mass: Float64Array;
  duration: number;
}

export function toTrack(sim: Simulation): Track {
  const { t_s, position_m, velocity_ms, mass_kg } = sim.trajectory;
  const n = t_s.length;
  const t = new Float64Array(t_s);
  const r = new Float64Array(n * 3);
  const v = new Float64Array(n * 3);
  for (let i = 0; i < n; i++) {
    const p = position_m[i]!;
    const q = velocity_ms[i]!;
    r[i * 3] = p[0];
    r[i * 3 + 1] = p[1];
    r[i * 3 + 2] = p[2];
    v[i * 3] = q[0];
    v[i * 3 + 1] = q[1];
    v[i * 3 + 2] = q[2];
  }
  return { t, r, v, mass: new Float64Array(mass_kg), duration: n ? t[n - 1]! : 0 };
}

/** Último índice i com t[i] <= tq (amostra pós-manobra quando há tempos repetidos). */
export function sampleIndex(t: Float64Array, tq: number): number {
  let lo = 0;
  let hi = t.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (t[mid]! <= tq) lo = mid + 1;
    else hi = mid;
  }
  return Math.max(0, lo - 1);
}

export interface StateOut {
  r: [number, number, number];
  v: [number, number, number];
  mass: number;
}

/** Estado interpolado em tq. Escreve em `out` para evitar alocações por quadro. */
export function stateAt(track: Track, tq: number, out: StateOut): StateOut {
  const n = track.t.length;
  if (n === 0) return out;
  const tc = Math.min(Math.max(tq, track.t[0]!), track.duration);
  const i = sampleIndex(track.t, tc);
  const j = Math.min(i + 1, n - 1);
  const t0 = track.t[i]!;
  const h = track.t[j]! - t0;
  out.mass = track.mass[i]!;
  if (h <= 0 || i === j) {
    for (let k = 0; k < 3; k++) {
      out.r[k] = track.r[i * 3 + k]!;
      out.v[k] = track.v[i * 3 + k]!;
    }
    return out;
  }
  const s = (tc - t0) / h;
  const s2 = s * s;
  const s3 = s2 * s;
  const h00 = 2 * s3 - 3 * s2 + 1;
  const h10 = s3 - 2 * s2 + s;
  const h01 = -2 * s3 + 3 * s2;
  const h11 = s3 - s2;
  const d00 = (6 * s2 - 6 * s) / h;
  const d10 = 3 * s2 - 4 * s + 1;
  const d01 = (-6 * s2 + 6 * s) / h;
  const d11 = 3 * s2 - 2 * s;
  for (let k = 0; k < 3; k++) {
    const p0 = track.r[i * 3 + k]!;
    const p1 = track.r[j * 3 + k]!;
    const m0 = track.v[i * 3 + k]!;
    const m1 = track.v[j * 3 + k]!;
    out.r[k] = h00 * p0 + h10 * h * m0 + h01 * p1 + h11 * h * m1;
    out.v[k] = d00 * p0 + d10 * m0 + d01 * p1 + d11 * m1;
  }
  return out;
}

export const newState = (): StateOut => ({ r: [0, 0, 0], v: [0, 0, 0], mass: 0 });
