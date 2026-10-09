import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "node:path"
import { fileURLToPath } from "node:url"

const directory = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(directory, "./src") } },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
})
