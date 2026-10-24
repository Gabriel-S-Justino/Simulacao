import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_DEV_API_PROXY ?? "http://localhost:8000" },
  },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          if (id.includes("node_modules/three/")) return "three";
          if (id.includes("node_modules/@react-three/")) return "r3f";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
  },
});
