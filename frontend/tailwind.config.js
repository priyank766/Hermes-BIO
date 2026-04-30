/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'JetBrains Mono', 'SF Mono', 'monospace'],
      },
      colors: {
        accent: { DEFAULT: '#34d399', dim: '#10b981' },
      },
    },
  },
  plugins: [],
};
