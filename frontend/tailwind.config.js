/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        vault: {
          50: '#f0f5fa',
          100: '#e1ecf5',
          200: '#c3d9eb',
          300: '#95bedc',
          400: '#5f9ecb',
          500: '#3981b5',
          600: '#286799',
          700: '#21537d',
          800: '#1b4162',
          900: '#0f2438',
          950: '#081420',
        }
      }
    },
  },
  plugins: [],
}
