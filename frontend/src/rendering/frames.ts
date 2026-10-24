/**
 * Conversão física → cena. A física usa ECI (Z para o polo norte, metros).
 * A cena Three.js é Y-up: cena = (x, z, -y) · escala. Coordenadas visuais
 * nunca retornam à física.
 */
export const METERS_PER_UNIT = 1_000_000; // 1 unidade de cena = 1000 km
export const EARTH_RADIUS_M = 6_378_137;

export function eciToScene(
  x: number,
  y: number,
  z: number,
  out: { set(x: number, y: number, z: number): unknown },
): void {
  out.set(x / METERS_PER_UNIT, z / METERS_PER_UNIT, -y / METERS_PER_UNIT);
}

/** Tempo sideral médio de Greenwich (IAU 1982), rad. Uso visual: orientar a textura da Terra. */
export function gmst(date: Date): number {
  const jd = date.getTime() / 86_400_000 + 2_440_587.5;
  const t = (jd - 2_451_545.0) / 36_525;
  const sec =
    67_310.54841 + (876_600 * 3600 + 8_640_184.812866) * t + 0.093104 * t * t - 6.2e-6 * t * t * t;
  const rad = ((sec % 86_400) / 86_400) * 2 * Math.PI;
  return (rad + 2 * Math.PI) % (2 * Math.PI);
}

/**
 * Direção aproximada do Sol em ECI (Astronomical Almanac, baixa precisão, ~0,01°).
 * Uso: direção da luz na cena. Não entra na propagação (modelo de dois corpos).
 */
export function sunDirectionEci(date: Date): [number, number, number] {
  const n = date.getTime() / 86_400_000 + 2_440_587.5 - 2_451_545.0;
  const deg = Math.PI / 180;
  const L = (280.46 + 0.9856474 * n) * deg;
  const g = (357.528 + 0.9856003 * n) * deg;
  const lambda = L + (1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * deg;
  const eps = (23.439 - 4e-7 * n) * deg;
  return [Math.cos(lambda), Math.cos(eps) * Math.sin(lambda), Math.sin(eps) * Math.sin(lambda)];
}
