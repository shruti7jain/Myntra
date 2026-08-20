/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        myntra: {
          pink: "#ff3f6c",
          orange: "#f16565",
          dark: "#1e1e24",
          surface: "#121217",
          card: "#181820",
          border: "#282834"
        }
      }
    },
  },
  plugins: [],
}
