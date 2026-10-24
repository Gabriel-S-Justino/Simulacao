import { describe, expect, it } from "vitest";
import { newState, sampleIndex, stateAt, type Track } from "../rendering/playback";

/** Movimento circular uniforme: x = R cos ωt, y = R sin ωt. Amostras grossas (1/16 de volta). */
function circleTrack(n: number, R = 7e6, omega = 1e-3): Track {
  const t = new Float64Array(n);
  const r = new Float64Array(n * 3);
  const v = new Float64Array(n * 3);
  const period = (2 * Math.PI) / omega;
  for (let i = 0; i < n; i++) {
    const ti = (i / (n - 1)) * period;
    t[i] = ti;
    r.set([R * Math.cos(omega * ti), R * Math.sin(omega * ti), 0], i * 3);
    v.set([-R * omega * Math.sin(omega * ti), R * omega * Math.cos(omega * ti), 0], i * 3);
  }
  return { t, r, v, mass: new Float64Array(n).fill(100), duration: t[n - 1]! };
}

describe("playback", () => {
  it("interpola com Hermite: erro pequeno entre amostras esparsas", () => {
    const tr = circleTrack(17);
    const out = newState();
    let maxErr = 0;
    for (let k = 0; k < 500; k++) {
      const tq = (k / 499) * tr.duration;
      stateAt(tr, tq, out);
      const ex = 7e6 * Math.cos(1e-3 * tq);
      const ey = 7e6 * Math.sin(1e-3 * tq);
      maxErr = Math.max(maxErr, Math.hypot(out.r[0] - ex, out.r[1] - ey));
    }
    // Erro relativo < 1e-4 com 16 segmentos por volta (interpolação apenas visual).
    expect(maxErr / 7e6).toBeLessThan(1e-4);
  });

  it("reproduz exatamente as amostras do núcleo", () => {
    const tr = circleTrack(9);
    const out = newState();
    stateAt(tr, tr.t[3]!, out);
    expect(out.r[0]).toBe(tr.r[9]);
    expect(out.r[1]).toBe(tr.r[10]);
  });

  it("em tempos repetidos (manobra), usa o estado pós-queima", () => {
    const t = new Float64Array([0, 10, 10, 20]);
    expect(sampleIndex(t, 10)).toBe(2);
    expect(sampleIndex(t, 9.99)).toBe(0);
    expect(sampleIndex(t, -5)).toBe(0);
    expect(sampleIndex(t, 50)).toBe(3);
  });

  it("limita o tempo ao intervalo simulado", () => {
    const tr = circleTrack(9);
    const out = newState();
    stateAt(tr, 1e12, out);
    expect(out.r[0]).toBeCloseTo(7e6, 0);
  });
});
