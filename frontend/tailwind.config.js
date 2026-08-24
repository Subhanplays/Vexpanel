/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vex: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          primary: '#3b82f6',
          primaryHover: '#2563eb',
          success: '#22c55e',
          warning: '#f59e0b',
          danger: '#ef4444',
          text: '#f1f5f9',
          textMuted: '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}