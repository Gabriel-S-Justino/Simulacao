import { create } from "zustand";

export interface LayerStatus {
  status: "loading" | "ok" | "unavailable";
  fetchedAt?: string;
}

interface LayerState {
  layers: Record<string, LayerStatus>;
  set: (id: string, s: LayerStatus) => void;
}

export const useLayerStatus = create<LayerState>((set) => ({
  layers: {},
  set: (id, s) => set((st) => ({ layers: { ...st.layers, [id]: s } })),
}));
