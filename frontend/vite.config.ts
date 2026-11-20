import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Localhost only: the dev server binds to 127.0.0.1 and forwards /api to the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: { host: "127.0.0.1" },
});
