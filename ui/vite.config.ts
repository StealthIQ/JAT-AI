import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@octogent/core": resolve(__dirname, "core/index.ts"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api/providers": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/prompts": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/terminals": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/terminal-snapshots": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/deck/tentacles": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/conversations": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/claude/usage": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
