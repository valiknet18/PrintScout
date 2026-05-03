import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Allow any host so tunnel domains (cloudflared, ngrok) work in dev.
    allowedHosts: true,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
})
