import { describe, expect, it } from "vitest";
import { geoToEarthLocal, gmst, sunDirectionEci } from "../rendering/frames";
import { duration } from "../utils/format";

describe("frames", () => {
  it("GMST na época J2000 ≈ 280,46°", () => {
    const deg = (gmst(new Date(Date.UTC(2000, 0, 1, 12, 0, 0))) * 180) / Math.PI;
    expect(deg).toBeCloseTo(280.46, 1);
  });

  it("Sol próximo ao equinócio de março tem declinação ~0", () => {
    const [x, y, z] = sunDirectionEci(new Date(Date.UTC(2024, 2, 20, 3, 6)));
    expect(Math.hypot(x, y, z)).toBeCloseTo(1, 10);
    expect(Math.abs(z)).toBeLessThan(0.01);
    expect(x).toBeGreaterThan(0.99);
  });

  it("Sol no solstício de junho tem declinação ≈ +23,44°", () => {
    const [, , z] = sunDirectionEci(new Date(Date.UTC(2024, 5, 20, 20, 51)));
    expect((Math.asin(z) * 180) / Math.PI).toBeCloseTo(23.44, 1);
  });

  it("lat/lon → referencial local da Terra (UV da SphereGeometry)", () => {
    const close = (a: number[], b: number[]) => a.forEach((v, i) => expect(v).toBeCloseTo(b[i]!, 12));
    close(geoToEarthLocal(0, 0, 1), [1, 0, 0]); // Greenwich no equador → +X
    close(geoToEarthLocal(0, 90, 1), [0, 0, -1]); // 90° E → −Z local (= +Y ECEF)
    close(geoToEarthLocal(90, 0, 2), [0, 2, 0]); // polo norte → +Y
    close(geoToEarthLocal(0, -180, 1), [-1, 0, 0]);
  });

  it("formata durações", () => {
    expect(duration(3661)).toBe("01:01:01");
    expect(duration(90061)).toBe("1d 01:01:01");
  });
});
