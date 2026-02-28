/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0e17',
        'bg-secondary': '#141926',
        'bg-tertiary': '#1c2333',
        'border-default': '#2a3450',
        'border-gold': '#c9a930',
        'accent-gold': '#f8d648',
        'accent-blue': '#3fc7eb',
        'text-primary': '#e8e6e0',
        'text-muted': '#8b8d91',
        wow: {
          'death-knight': '#C41E3A',
          druid: '#FF7C0A',
          hunter: '#AAD372',
          mage: '#3FC7EB',
          paladin: '#F48CBA',
          priest: '#FFFFFF',
          rogue: '#FFF468',
          shaman: '#0070DD',
          warlock: '#8788EE',
          warrior: '#C69B6D'
        }
      },
      fontFamily: {
        wow: ['"LifeCraft"', '"Cinzel"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      boxShadow: {
        gold: '0 0 12px rgba(201, 169, 48, 0.4)',
        'gold-lg': '0 0 24px rgba(201, 169, 48, 0.6)'
      }
    }
  },
  plugins: []
}
