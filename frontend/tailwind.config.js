/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: 'var(--paper)',
        surface: 'var(--surface)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        hairline: 'var(--hairline)',
        tinte: 'var(--tinte)',
        'tinte-strong': 'var(--tinte-strong)',
        btn: 'var(--btn)',
        'btn-strong': 'var(--btn-strong)',
        'btn-ink': 'var(--btn-ink)',
        unread: 'var(--unread)',
        hover: 'var(--hover)',
        tint: 'var(--tint)',
        danger: 'var(--danger)',
        'danger-bg': 'var(--danger-bg)',
        success: 'var(--success)',
        'success-bg': 'var(--success-bg)',
        warm: 'var(--warm)',
        'warm-bg': 'var(--warm-bg)',
      },
      fontFamily: {
        sans: ['"Instrument Sans Variable"', 'system-ui', 'sans-serif'],
        serif: ['Newsreader', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      transitionDuration: {
        DEFAULT: '120ms',
      },
    },
  },
  plugins: [],
}
