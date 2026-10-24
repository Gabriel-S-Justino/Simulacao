import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { DesignIn } from "../types/contracts";
import { api } from "./api";

export const useCatalog = () =>
  useQuery({ queryKey: ["catalog"], queryFn: api.catalog, staleTime: Infinity, retry: 2 });

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export const useDesignReport = (design: DesignIn) => {
  const d = useDebounced(design, 150);
  return useQuery({
    queryKey: ["evaluate", d],
    queryFn: ({ signal }) => api.evaluate(d, signal),
    placeholderData: keepPreviousData,
    retry: false,
  });
};

export const useHohmann = (initialKm: number, targetKm: number, design: DesignIn) => {
  const args = useDebounced({ initialKm, targetKm, design }, 200);
  return useQuery({
    queryKey: ["hohmann", args],
    queryFn: ({ signal }) =>
      api.hohmann(
        {
          initial_altitude_m: args.initialKm * 1000,
          target_altitude_m: args.targetKm * 1000,
          design: args.design,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    retry: false,
  });
};

export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 30_000, retry: 1 });

/** Persistência disponível (backend com banco configurado e acessível). */
export const usePersistence = () => useHealth().data?.database === "ok";

export const useMissions = (enabled: boolean) =>
  useQuery({ queryKey: ["missions"], queryFn: api.missions, enabled, retry: false });

export const useCheckpoints = (missionId: string | null) =>
  useQuery({
    queryKey: ["checkpoints", missionId],
    queryFn: () => api.checkpoints(missionId!),
    enabled: missionId !== null,
    retry: false,
  });

// ---------- Fontes externas ----------

export const useIssPosition = (enabled: boolean) =>
  useQuery({
    queryKey: ["iss"],
    queryFn: api.issPosition,
    enabled,
    refetchInterval: 15_000,
    retry: false,
  });

export const useEarthEvents = (enabled: boolean) =>
  useQuery({
    queryKey: ["earth-events"],
    queryFn: () => api.earthEvents(),
    enabled,
    staleTime: 10 * 60_000,
    retry: false,
  });

export const useSpaceWeather = (enabled: boolean) =>
  useQuery({
    queryKey: ["space-weather"],
    queryFn: () => api.spaceWeather(),
    enabled,
    staleTime: 10 * 60_000,
    retry: false,
  });

export const useGibsLayers = (enabled: boolean) =>
  useQuery({
    queryKey: ["gibs-layers"],
    queryFn: api.gibsLayers,
    enabled,
    staleTime: 60 * 60_000,
    retry: false,
  });
