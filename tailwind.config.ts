import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        saag: {
          DEFAULT: "#1F3A28",
          dark: "#132318",
          light: "#2F5138",
          rim: "#3E6B49",
        },
        turmeric: {
          DEFAULT: "#E8A33D",
          dim: "#C98A2E",
        },
        ember: {
          DEFAULT: "#C1502E",
          dim: "#9C3F24",
        },
        paper: {
          DEFAULT: "#F3EEE1",
          dim: "#E7E0CC",
        },
        steel: "#8B8677",
        cream: "#EDE7D8",
        ink: "#161510",
      },
      fontFamily: {
        display: [
          '"Century Gothic"',
          '"Futura"',
          '"Trebuchet MS"',
          '"Segoe UI"',
          "sans-serif",
        ],
        body: [
          '"Segoe UI"',
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        mono: [
          '"SFMono-Regular"',
          "Consolas",
          '"Liberation Mono"',
          "Menlo",
          "monospace",
        ],
      },
      keyframes: {
        drawline: {
          "0%": { strokeDashoffset: "100" },
          "100%": { strokeDashoffset: "0" },
        },
        risein: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        ringspin: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        blip: {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        drawline: "drawline 1.8s ease-out 0.2s forwards",
        risein: "risein 0.7s ease-out forwards",
        ringspin: "ringspin 60s linear infinite",
        blip: "blip 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
