import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#0F1117',
        surface:  '#1A1D27',
        surface2: '#21252F',
        border:   '#2D3143',
        accent:   '#F97316',
        'accent-hover': '#EA6C0A',
        success:  '#22C55E',
        danger:   '#EF4444',
        running:  '#3B82F6',
        muted:    '#6B7280',
        'text-primary': '#F1F5F9',
        'text-muted':   '#64748B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card:  '8px',
        badge: '4px',
        input: '6px',
      },
      animation: {
        'pulse-blue': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
