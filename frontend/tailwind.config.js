/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#f7f7f4',
        ink: '#26251e',
        body: '#5a5852',
        muted: '#807d72',
        card: '#ffffff',
        hairline: '#e6e5e0',
        cta: '#f54e00',
        'cta-hover': '#d04200',
        success: '#1f8a65',
        error: '#cf2d56',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        button: '8px',
        card: '12px',
      },
      spacing: {
        section: '80px',
      },
    },
  },
  plugins: [],
}
