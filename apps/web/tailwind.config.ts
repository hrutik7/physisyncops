import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111315",
        muted: "#667085",
        line: "#E5E7EB",
        panel: "#F7F8FA",
        graphite: "#2C3137",
        success: "#087443",
        warning: "#B54708",
        danger: "#B42318",
        accent: "#2563EB",
        teal: "#0F766E"
      },
      boxShadow: {
        "soft-border": "0 0 0 1px rgba(17, 19, 21, 0.08), 0 12px 40px rgba(17, 19, 21, 0.06)"
      }
    }
  },
  plugins: []
};

export default config;
