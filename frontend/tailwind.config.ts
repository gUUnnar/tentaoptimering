import type { Config } from "tailwindcss"

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: { fontFamily: { sans: ["\"Helvetica Neue\"", "Helvetica", "Arial", "sans-serif"] } } },
  plugins: [],
} satisfies Config
