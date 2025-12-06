/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Flow status colors
        'flow-low': '#3b82f6',      // blue-500
        'flow-normal': '#10b981',   // green-500
        'flow-high': '#f59e0b',     // amber-500
        'flow-very-high': '#ef4444', // red-500
      },
    },
  },
  plugins: [],
}
