/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./core/templates/**/*.html",
    "./hoteis/templates/**/*.html",
    "./clientes/templates/**/*.html",
    "./parceiros/templates/**/*.html",
    "./cinema/templates/**/*.html",
    "./eventos/templates/**/*.html",
    "./parques/templates/**/*.html",
    "./administracao/templates/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        'action-blue': '#2563eb',
        'action-blue-dark': '#1d4ed8'
      },
      fontFamily: {
        'sans': ['Poppins', 'sans-serif'],
        'display': ['Quicksand', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
