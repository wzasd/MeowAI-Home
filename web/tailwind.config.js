/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cat: {
          orange: '#f97316',
          inky: '#8b5cf6',
          patch: '#ec4899',
        }
      }
    },
  },
  plugins: [],
}
