/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#E9FFF9',
          100: '#D1FFF4',
          200: '#A3FFE9',
          300: '#75FFDE',
          400: '#47FFD3',
          500: '#2AC7A5',
          600: '#1F9F84',
          700: '#147763',
          800: '#0A4F42',
          900: '#052721',
        },
        dark: {
          50: '#F0F9F8',
          100: '#E0F3F1',
          200: '#C1E7E3',
          300: '#A2DBD5',
          400: '#83CFC7',
          500: '#0A1F1C',
          600: '#08302B',
          700: '#062520',
          800: '#041A15',
          900: '#020F0B',
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'display': ['Satoshi', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-in': 'slideIn 0.8s ease-out forwards',
        'fade-in': 'fadeIn 1s ease-out forwards',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(42, 199, 165, 0.3)' },
          '100%': { boxShadow: '0 0 30px rgba(42, 199, 165, 0.6)' },
        },
        slideIn: {
          '0%': { transform: 'translateY(50px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      }
    },
  },
  plugins: [],
}

