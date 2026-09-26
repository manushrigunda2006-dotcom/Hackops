import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The acceptance checker talks to the backend directly (see .dogfood.toml).
// The React dev server proxies /api calls to it so the UI works the same
// way in dev as it will behind whatever we put in docker-compose.
//
// The proxy target is overridable via BACKEND_PROXY_TARGET because it
// differs by context: plain `npm run dev` on a laptop reaches the
// backend at localhost, but inside docker-compose the frontend
// container has to address it by service name instead.
const backendTarget = process.env.BACKEND_PROXY_TARGET || "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
});
