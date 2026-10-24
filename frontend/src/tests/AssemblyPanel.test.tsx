import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AssemblyPanel } from "../features/spacecraft-assembly/AssemblyPanel";
import { DEFAULT_PARTS, useMission } from "../stores/missionStore";

const catalog = {
  version: "t",
  notice: "Fictício.",
  components: [
    {
      id: "eng-biprop-400", name: "Motor 400 N", category: "propulsion_engine", mass_kg: 4.3,
      dimensions_m: [0.3, 0.3, 0.65], power_consumption_w: 10, power_generation_w: 0, cost_musd: 1,
      reliability: 0.99, fictional: true, source: "f", params: { thrust_n: 400, isp_s: 318, propellant: "mmh_nto" },
    },
  ],
};

const report = (dv: number) => ({
  valid: true, stages: [], dry_mass_kg: 100, propellant_kg: 50, wet_mass_kg: 150, final_mass_kg: 100,
  total_delta_v_ms: dv, power_generation_w: 600, power_consumption_w: 200, power_margin_w: 400,
  battery_capacity_wh: 0, cost_musd: 5, reliability: 0.9, contains_fictional: true, issues: [],
});

afterEach(() => {
  vi.restoreAllMocks();
  useMission.setState({ parts: DEFAULT_PARTS });
});

describe("AssemblyPanel", () => {
  it("envia a montagem ao backend e mostra o delta-v calculado", async () => {
    const bodies: unknown[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      if (String(url).includes("catalog")) return new Response(JSON.stringify(catalog));
      bodies.push(JSON.parse(String(init?.body)));
      return new Response(JSON.stringify(report(bodies.length === 1 ? 1234 : 0)));
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AssemblyPanel />
      </QueryClientProvider>,
    );
    await screen.findByText("1.234");
    await userEvent.click(screen.getByRole("button", { name: "Remover Motor 400 N" }));
    await waitFor(() => expect(bodies.length).toBe(2));
    const last = bodies[1] as { stages: { parts: { component_id: string }[] }[] };
    expect(last.stages[0]!.parts.some((p) => p.component_id === "eng-biprop-400")).toBe(false);
    await waitFor(() =>
      expect(screen.getByText("Delta-v").parentElement).toHaveTextContent(/^Delta-v0m\/s$/),
    );
  });
});
