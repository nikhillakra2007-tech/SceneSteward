/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "var(--border)",
        slate: {
          50: "#f2f6f3",
          100: "#e3eae5",
          200: "#c5d2c9",
          300: "#9db0a4",
          400: "#71857a",
          500: "#54655c",
          600: "#3d4b43",
          700: "#2c3831",
          800: "#1e2823",
          850: "#161f1a",
          900: "#101714",
          950: "#0a100d",
        },
        emerald: {
          50: "#edf7f0",
          100: "#d4ecdd",
          200: "#a9d9bc",
          300: "#7cc499",
          400: "#55ab7c",
          500: "#379566",
          600: "#267952",
          700: "#1f6143",
          800: "#1a4d37",
          900: "#143b2b",
          950: "#0a2418",
        },
        brass: {
          300: "#e6c98a",
          400: "#d9b66a",
          500: "#c9a45c",
          600: "#a98543",
          700: "#7f6434",
        },
      },
    },
  },
  plugins: [],
};
