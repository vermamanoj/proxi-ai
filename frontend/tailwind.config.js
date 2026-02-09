/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./hooks/**/*.{js,ts,jsx,tsx}",
    "./services/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        proxi: {
          black: '#0a0a0a',
          dark: '#111111',
          gray: '#222222',
          accent: '#00f0ff',
          success: '#00ff9d',
          warning: '#ffb86c',
          error: '#ff5555',
        },
        th: {
          base: 'rgb(var(--th-base) / <alpha-value>)',
          surface: 'rgb(var(--th-surface) / <alpha-value>)',
          'surface-alt': 'rgb(var(--th-surface-alt) / <alpha-value>)',
          hover: 'rgb(var(--th-hover) / <alpha-value>)',
          text: 'rgb(var(--th-text) / <alpha-value>)',
          'text-sec': 'rgb(var(--th-text-sec) / <alpha-value>)',
          'text-muted': 'rgb(var(--th-text-muted) / <alpha-value>)',
          border: 'rgb(var(--th-border) / <alpha-value>)',
          accent: 'rgb(var(--th-accent) / <alpha-value>)',
          input: 'rgb(var(--th-input) / <alpha-value>)',
          code: 'rgb(var(--th-code-bg) / <alpha-value>)',
          overlay: 'rgb(var(--th-overlay) / <alpha-value>)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['SF Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}