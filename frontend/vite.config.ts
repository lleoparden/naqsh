import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Match the documented backend command (`uvicorn app.main:app --port 8000`).
// Override with NAQSH_API when the backend runs elsewhere (e.g. a second instance).
const apiTarget = process.env.NAQSH_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
  preview: {
    port: 4174,
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
});
