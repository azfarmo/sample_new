// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = { // Using module.exports for standard CRA setups
  content: [
    "./src/**/*.{js,jsx,ts,tsx}", // Watches all JS, JSX, TS, TSX files in src
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        lukso: {
          DEFAULT: '#6241C5', // Official LUKSO Purple (slightly adjusted from previous examples to common branding)
          'light': '#8A71D8',
          'dark': '#493092',
          'pink': '#E91E63', // A common accent pink, LUKSO also uses FC007A
          'secondary-pink': '#FC007A',
        },
        gray: { // Example of extending or overriding gray palette for dark mode
          900: '#121212', // Darker background
          800: '#1E1E1E', // Slightly lighter bg for cards
          700: '#2C2C2C', // Borders, secondary elements
          600: '#3A3A3A',
          400: '#A0A0A0', // Lighter text
          200: '#E0E0E0', // Primary text
          100: '#F5F5F5',
        }
      },
      fontFamily: {
        // Add custom fonts if you have them
        // sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'), // For better default styling of form elements
  ],
}