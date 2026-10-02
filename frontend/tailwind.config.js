/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand green — matches Dangme Community Bank's institutional palette.
        // brand-500 is an exact sample from their site header (#3d8b43).
        brand: {
          50:  "#f0f9f1",
          100: "#dcf0de",
          200: "#bbe1c0",
          300: "#8dcb95",
          400: "#5cae66",
          500: "#3d8b43",   // primary accent (matches bank header)
          600: "#2f7034",   // sidebar + primary buttons
          700: "#275a2b",   // hover / pressed
          800: "#224a25",
          900: "#1d3e20",
        },
      },
    },
  },
  plugins: [],
};