import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // EVE Online dark theme
        background: '#000000',
        card: '#1c1c1e',
        'card-hover': '#2c2c2e',
        border: '#38383a',
        primary: '#0a84ff',
        'primary-hover': '#0070e0',
        text: '#ffffff',
        'text-secondary': '#8e8e93',

        // Security status colors
        'high-sec': '#00ff00',
        'low-sec': '#ffaa00',
        'null-sec': '#ff0000',
        wormhole: '#9900ff',

        // Risk level colors
        'risk-green': '#32d74b',
        'risk-yellow': '#ffd60a',
        'risk-orange': '#ff9f0a',
        'risk-red': '#ff453a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};

export default config;
