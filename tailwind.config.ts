import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0A1647", blue: "#1E4FE0", electric: "#2E8BFF", sky: "#8CC8FF", ice: "#EEF4FF",
        ok: "#12B76A", warn: "#F79009", bad: "#D92D20",
      },
      fontFamily: {
        sans: ["var(--f)", "system-ui", "sans-serif"],
        display: ["var(--h)", "var(--f)", "system-ui", "sans-serif"],
        mono: ["var(--m)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
