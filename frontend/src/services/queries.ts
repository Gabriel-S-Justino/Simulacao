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
