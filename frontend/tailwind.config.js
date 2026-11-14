/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#00174b',
          800: '#0a235c',
          700: '#14316d',
        },
        primary: {
          DEFAULT: '#0051d5',
          dark: '#003ea7',
          light: '#276afa',
          tint: '#dbe1ff',
        },
        surface: {
          DEFAULT: '#f8f9ff',
          dim: '#d8dae1',
          container: '#f1f3fa',
          lowest: '#ffffff',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Hanken Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
