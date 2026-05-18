import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#0F1117',
        surface:  '#1A1D27',
        surface2: '#21252F',
        surface3: '#2A2F3D',
        border:   '#2D3143',
        accent:   '#F97316',
        'accent-hover': '#FB8438',
        success:  '#22C55E',
        danger:   '#EF4444',
        running:  '#3B82F6',
        warn:     '#F59E0B',
        muted:    '#64748B',
        'text-primary': '#F1F5F9',
        'text-2':       '#CBD5E1',
        'text-muted':   '#64748B',
        'text-dim':     '#475569',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card:  '12px',
        badge: '999px',
        input: '8px',
      },
    },
  },
  plugins: [],
} satisfies Config
