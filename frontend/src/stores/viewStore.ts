import { create } from "zustand";

export type Focus = "craft" | "earth";
export type Quality = "low" | "medium" | "high";

interface ViewState {
  focus: Focus;
  quality: Quality;
  autoQuality: boolean;
  dpr: number;
  setFocus: (f: Focus) => void;
  setQuality: (q: Quality) => void;
  setAutoQuality: (a: boolean) => void;
  setDpr: (d: number) => void;
}

export const QUALITY_DPR: Record<Quality, number> = { low: 1, medium: 1.5, high: 2 };

export const useView = create<ViewState>((set) => ({
  focus: "craft",
  quality: "high",
  autoQuality: true,
  dpr: 2,
  setFocus: (focus) => set({ focus }),
  setQuality: (quality) => set({ quality, dpr: QUALITY_DPR[quality] }),
  setAutoQuality: (autoQuality) => set({ autoQuality }),
  setDpr: (dpr) => set({ dpr }),
}));
