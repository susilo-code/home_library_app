/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./library/templates/**/*.html",
    // PENTING: kelas Tailwind juga dipakai dari kode Python (widget attrs di
    // library/forms.py & co). Tanpa baris ini kelas seperti `pl-11` pada input
    // login TIDAK pernah tergenerate ke output.css — ikon dan teks saling
    // bertimpa di PC yang memakai CSS lokal (tanpa Node/CDN). Diaudit oleh
    // scripts/dev/cek_css_lokal.py.
    "./library/**/*.py",
    "./config/**/*.py",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'deep-purple': {
          50: '#f5f0ff',
          100: '#ebe0ff',
          200: '#d6c6ff',
          300: '#b899ff',
          400: '#9a6eff',
          500: '#8A4FFF',
          600: '#742eff',
          700: '#5f1ce6',
          800: '#4c18b8',
          900: '#3e1692',
          950: '#2E1A47',
        },
        'purple-slate': {
          50: '#f7f5fa',
          100: '#efe9f4',
          200: '#dfd2e9',
          300: '#c8b2d6',
          400: '#a889bb',
          500: '#8b6b9e',
          600: '#735384',
          700: '#5e436c',
          800: '#4e385a',
          900: '#40304a',
          950: '#1A1126',
        },
        // Palet berikut dipakai halaman login & modal. Sebelumnya hanya
        // didefinisikan di config Tailwind CDN (inline), sehingga kelasnya
        // TIDAK ikut tergenerate ke output.css — tampilan bisa rusak di PC
        // yang memakai CSS lokal (tanpa Node/CDN). Kini didefinisikan di sini.
        'ink': {
          600: '#1E0B2E',
          700: '#1A0F2B',
          800: '#12081F',
          900: '#0D0517',
        },
        'royal': {
          400: '#A97BFF',
          500: '#8A4FFF',
          600: '#742EFF',
          700: '#5F1CE6',
          800: '#4B14B8',
          900: '#3B1E54',
        },
        'plum': {
          400: '#8B6AA0',
          500: '#735384',
          600: '#63446F',
          700: '#522B5B',
          800: '#40214A',
          900: '#2E1A47',
        },
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'display': ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}