/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Playfair Display"', "serif"],
        body: ['"DM Sans"', "sans-serif"],
      },
      colors: {
        patch: {
          bg: "#0a0506",
          card: "#1a0d10",
          border: "#2d1219",
          accent: "#e11d48",
          glow: "#fb7185",
          soft: "#fecdd3",
          muted: "#6b2130",
        },
      },
      keyframes: {
        "slide-up": {
          "0%": { transform: "translateY(20px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(225,29,72,0.3)" },
          "50%": { boxShadow: "0 0 40px rgba(225,29,72,0.6)" },
        },
        ripple: {
          "0%": { transform: "scale(1)", opacity: "0.4" },
          "100%": { transform: "scale(3)", opacity: "0" },
        },
      },
      animation: {
        "slide-up": "slide-up 0.5s ease-out",
        "glow-pulse": "glow-pulse 2s ease-in-out infinite",
        ripple: "ripple 1.5s ease-out infinite",
      },
    },
  },
  plugins: [],
};
