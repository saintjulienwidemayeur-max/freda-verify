import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--f)", "system-ui", "sans-serif"],
        mono: ["var(--m)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
