/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sat: {
          bg: "#090B0E",
          surface: "#0F1218",
          panel: "#141822",
          card: "#191E2A",
          border: "#242B3B",
          borderLight: "#333C50",
          text: "#F1F5F9",
          muted: "#94A3B8",
          dim: "#64748B",
          accent: "#38BDF8", // primary analysis sky blue
          change: "#FF5533", // warning/change laser orange
          stable: "#10B981", // stable emerald green
          sar: "#A855F7",    // radar violet
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-sweep': 'sweep 4s linear infinite',
      },
      keyframes: {
        sweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        }
      }
    },
  },
  plugins: [],
}
