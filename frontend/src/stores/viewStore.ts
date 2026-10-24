import { create } from "zustand";

export type Focus = "craft" | "earth";
export type Quality = "low" | "medium" | "high";
export type DayLayer = "blue-marble" | "viirs-daily";

interface ViewState {
  focus: Focus;
  quality: Quality;
  autoQuality: boolean;
  dpr: number;
  liveOpen: boolean;
  showEvents: boolean;
  showIss: boolean;
  dayLayer: DayLayer;
  setFocus: (f: Focus) => void;
  setQuality: (q: Quality) => void;
  setAutoQuality: (a: boolean) => void;
  setDpr: (d: number) => void;
  toggleLive: () => void;
  setShowEvents: (v: boolean) => void;
  setShowIss: (v: boolean) => void;
  setDayLayer: (l: DayLayer) => void;
}

export const QUALITY_DPR: Record<Quality, number> = { low: 1, medium: 1.5, high: 2 };

export const useView = create<ViewState>((set) => ({
  focus: "craft",
  quality: "high",
  autoQuality: true,
  dpr: 2,
  liveOpen: false,
  showEvents: false,
  showIss: false,
  dayLayer: "blue-marble",
  setFocus: (focus) => set({ focus }),
  setQuality: (quality) => set({ quality, dpr: QUALITY_DPR[quality] }),
  setAutoQuality: (autoQuality) => set({ autoQuality }),
  setDpr: (dpr) => set({ dpr }),
  toggleLive: () => set((s) => ({ liveOpen: !s.liveOpen })),
  setShowEvents: (showEvents) => set({ showEvents }),
  setShowIss: (showIss) => set({ showIss }),
  setDayLayer: (dayLayer) => set({ dayLayer }),
}));
