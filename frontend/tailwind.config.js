/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Primary — Indigo
        primary: '#533afd',
        'primary-deep': '#4434d4',
        'primary-press': '#2e2b8c',
        'primary-soft': '#665efd',
        'primary-subdued': '#b9b9f9',
        'brand-dark': '#1c1e54',

        // Text
        ink: '#0d253d',
        'ink-secondary': '#273951',
        'ink-mute': '#64748d',
        'ink-mute-2': '#61718a',
        'on-primary': '#ffffff',

        // Surfaces
        canvas: '#ffffff',
        'canvas-soft': '#f6f9fc',
        'canvas-cream': '#f5e9d4',
        hairline: '#e3e8ee',
        'hairline-input': '#a8c3de',

        // Accent
        ruby: '#ea2261',
        magenta: '#f96bee',
        lemon: '#9b6829',
        'shadow-blue': '#003770',

        // Semantic
        success: '#1f8a65',
        error: '#cf2d56',
      },
      fontFamily: {
        sans: ["'Inter'", 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        xs: '4px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        pill: '9999px',
      },
      spacing: {
        xxs: '2px',
        xs: '4px',
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        xxl: '32px',
        huge: '64px',
      },
      fontSize: {
        'display-xxl': ['56px', { lineHeight: '1.03', fontWeight: '300', letterSpacing: '-1.4px' }],
        'display-xl': ['48px', { lineHeight: '1.15', fontWeight: '300', letterSpacing: '-0.96px' }],
        'display-lg': ['32px', { lineHeight: '1.1', fontWeight: '300', letterSpacing: '-0.64px' }],
        'display-md': ['26px', { lineHeight: '1.12', fontWeight: '300', letterSpacing: '-0.26px' }],
        'heading-lg': ['22px', { lineHeight: '1.1', fontWeight: '300', letterSpacing: '-0.22px' }],
        'heading-md': ['20px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '-0.2px' }],
        'heading-sm': ['18px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '0' }],
        'body-lg': ['16px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '0' }],
        'body-md': ['15px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '0' }],
        'body-tabular': ['14px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '-0.42px' }],
        'button-md': ['16px', { lineHeight: '1.0', fontWeight: '400', letterSpacing: '0' }],
        'button-sm': ['14px', { lineHeight: '1.0', fontWeight: '400', letterSpacing: '0' }],
        caption: ['13px', { lineHeight: '1.4', fontWeight: '400', letterSpacing: '-0.39px' }],
        micro: ['11px', { lineHeight: '1.4', fontWeight: '300', letterSpacing: '0' }],
        'micro-cap': ['10px', { lineHeight: '1.15', fontWeight: '400', letterSpacing: '0.1px' }],
      },
      boxShadow: {
        'card': 'rgba(0,55,112,0.08) 0 1px 3px',
        'card-hover': 'rgba(0,55,112,0.08) 0 8px 24px, rgba(0,55,112,0.04) 0 2px 6px',
        'float': 'rgba(0,55,112,0.08) 0 8px 24px, rgba(0,55,112,0.04) 0 2px 6px',
      },
    },
  },
  plugins: [],
}
