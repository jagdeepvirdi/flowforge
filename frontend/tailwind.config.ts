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
        'text-3':       'var(--text-3)',
        'text-muted':   '#64748B',
        'text-dim':     '#475569',

        // Remaining tokens from src/index.css :root not yet mapped above.
        // Referenced via var() (not hardcoded) so they always match the CSS source of truth.
        'border-strong': 'var(--border-strong)',
        'accent-soft':   'var(--accent-soft)',
        'accent-glow':   'var(--accent-glow)',
        'success-soft':  'var(--success-soft)',
        failure:         'var(--failure)',
        'failure-soft':  'var(--failure-soft)',
        'running-soft':  'var(--running-soft)',
        'warn-soft':     'var(--warn-soft)',
        'failure-text':  'var(--failure-text)',
        'success-text':  'var(--success-text)',
        'running-text':  'var(--running-text)',
        'accent-text':   'var(--accent-text)',
        'bg-code':       'var(--bg-code)',
        'surface-hover': 'var(--surface-hover)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card:  '12px',
        badge: '999px',
        input: '8px',
        'r-sm': 'var(--r-sm)',
        r:      'var(--r)',
        'r-lg': 'var(--r-lg)',
        'r-xl': 'var(--r-xl)',
      },
      boxShadow: {
        card: 'var(--shadow)',
      },
    },
  },
  plugins: [],
} satisfies Config
