import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    '../../packages/ui_kit/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0B5D4B',
          soft: '#E3F1EC',
          dark: '#08483A',
        },
        attention: {
          DEFAULT: '#C77D0A',
          soft: '#FFF3DC',
        },
        urgent: {
          DEFAULT: '#B3261E',
          soft: '#FDECEA',
        },
        neutral: {
          bg: '#F8FAFC',
          card: '#FFFFFF',
          text: '#12343B',
        },
      },
      fontFamily: {
        bangla: ['Noto Sans Bengali', 'sans-serif'],
        sans: ['Inter', 'Noto Sans Bengali', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
