/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API calls to the local FastAPI backend so the
// browser never makes a cross-origin request during local development --
// no CORS_ALLOWED_ORIGINS setup needed just to run `npm run dev` against
// `uv run uvicorn glue.app:app --reload`. A built/deployed frontend on a
// different origin than the API still needs CORS_ALLOWED_ORIGINS set on
// the backend (see .env.example) since there's no dev-server proxy then.
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": API_PROXY_TARGET,
      "/health": API_PROXY_TARGET,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
