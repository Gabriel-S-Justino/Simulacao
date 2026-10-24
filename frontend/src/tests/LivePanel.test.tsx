import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LivePanel, classRank } from "../features/live-data/LivePanel";
import { eventPoints } from "../rendering/celestial-bodies/GeoMarkers";
import { useView } from "../stores/viewStore";

const base = {
  fetched_at: "2024-05-10T12:00:00Z",
  observed_at: null,
  valid_time_start: null,
  valid_time_end: null,
  stale: false,
  units: {},
  reference_frame: null,
  uncertainty: null,
  notes: [],
  attribution: null,
};
const failed = (source: string) => ({
  ...base,
  source,
  status: "error",
  data: null,
  error: { code: "connection", message: "Falha de conexão (ConnectError).", retryable: true },
});

function renderPanel() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <LivePanel />
    </QueryClientProvider>,
  );
}

describe("LivePanel", () => {
  beforeEach(() => useView.setState({ liveOpen: true, showEvents: false, showIss: false }));
  afterEach(() => vi.unstubAllGlobals());

  it("mostra a falha da fonte em vez de valores", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const body = url.includes("space-weather")
          ? {
              start: "2024-05-03",
              end: "2024-05-10",
              flares: failed("NASA DONKI FLR"),
              storms: failed("NASA DONKI GST"),
              cmes: failed("NASA DONKI CME"),
            }
          : failed("Open Notify ISS");
        return new Response(JSON.stringify(body), { status: 200 });
      }),
    );
    renderPanel();
    expect(await screen.findByText(/NASA DONKI FLR: indisponível/)).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(3);

    fireEvent.click(screen.getByLabelText(/Estação Espacial/));
    expect(await screen.findByText(/Open Notify ISS: indisponível/)).toBeInTheDocument();
    expect(screen.queryByText(/observado/)).not.toBeInTheDocument();
  });

  it("indica backend fora do ar", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    renderPanel();
    await waitFor(() => expect(screen.getByText("backend indisponível")).toBeInTheDocument());
  });
});

describe("auxiliares", () => {
  it("ordena classes GOES", () => {
    expect(classRank("X3.9")).toBeGreaterThan(classRank("M9.9"));
    expect(classRank("M1.0")).toBeGreaterThan(classRank("C9.0"));
    expect(classRank("?")).toBe(-1);
  });

  it("usa a geometria mais recente de cada evento", () => {
    const pts = eventPoints([
      {
        id: "e",
        title: "t",
        link: null,
        closed: null,
        categories: [{ id: "wildfires", title: "Wildfires" }],
        geometry: [
          { date: "a", kind: "point", lon_deg: 1, lat_deg: 2, point_method: "point", magnitude_value: null, magnitude_unit: null },
          { date: "b", kind: "point", lon_deg: 3, lat_deg: 4, point_method: "point", magnitude_value: null, magnitude_unit: null },
        ],
      },
    ]);
    expect(pts).toEqual([{ lat: 4, lon: 3, color: "#ff7a45" }]);
  });
});
