/** Medição de tempo por quadro (anel de 600 amostras) para a interface e para docs/performance.md. */
const N = 600;
const buf = new Float32Array(N);
let idx = 0;
let filled = 0;

export function recordFrame(ms: number): void {
  buf[idx] = ms;
  idx = (idx + 1) % N;
  filled = Math.min(filled + 1, N);
}

export function frameStats(): { fps: number; p50: number; p95: number; p99: number } | null {
  if (filled < 30) return null;
  const arr = Array.from(buf.subarray(0, filled)).sort((a, b) => a - b);
  const q = (p: number) => arr[Math.min(arr.length - 1, Math.floor(p * arr.length))]!;
  const mean = arr.reduce((s, x) => s + x, 0) / arr.length;
  return { fps: 1000 / mean, p50: q(0.5), p95: q(0.95), p99: q(0.99) };
}
