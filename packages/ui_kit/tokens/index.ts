/**
 * AIN-AI Design Tokens (SRS Section 10.2)
 */

export const colors = {
  primary: '#0B5D4B',          // Deep Green
  primarySoft: '#E3F1EC',      // Soft Green Tint
  attention: '#C77D0A',        // Amber (AI Label, Needs-Check)
  attentionSoft: '#FFF3DC',    // Soft Amber
  urgent: '#B3261E',           // Crimson Red (Urgent Only)
  urgentSoft: '#FDECEA',       // Soft Red
  neutral: {
    bg: '#F8FAFC',
    card: '#FFFFFF',
    border: '#E2E8F0',
    textMain: '#12343B',
    textMuted: '#64748B',
    darkBg: '#0F172A',
    darkCard: '#1E293B',
    darkBorder: '#334155'
  }
};

export const brand = {
  primary: '#0B5D4B',
  primaryDark: '#073E32',
  accent: '#0284c7'
};

export const status = {
  success: { bg: '#E3F1EC', text: '#0B5D4B', border: '#A7D7C5' },
  warning: { bg: '#FFF3DC', text: '#C77D0A', border: '#FDE1A9' },
  error: { bg: '#FDECEA', text: '#B3261E', border: '#F9B7B2' },
  info: { bg: '#E0F2FE', text: '#0369A1', border: '#BAE6FD' }
};

export const typography = {
  fontFamilyBangla: "'Noto Sans Bengali', sans-serif",
  fontFamilyLatin: "'Inter', sans-serif",
  lineHeightBangla: 1.6,
  bodyMinPx: 16,
  touchTargetMinPx: 48,
  cardRadiusPx: 12
};

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  touchTarget: '48px'
};

export const elevation = {
  none: 'none',
  card: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
  modal: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
  floating: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
};

export const radius = {
  none: '0px',
  sm: '6px',
  md: '8px',
  card: '12px',
  full: '9999px'
};

export const breakpoints = {
  mobileMax: 639,
  tabletMin: 640,
  tabletMax: 1023,
  desktopMin: 1024,
  // CSS media query helpers
  mobile: '@media (max-width: 639px)',
  tablet: '@media (min-width: 640px) and (max-width: 1023px)',
  desktop: '@media (min-width: 1024px)',
  tabletUp: '@media (min-width: 640px)',
};

export const layout = {
  containerMaxWidth: '1280px',
  sidebarWidthDesktop: '260px',
  sidebarWidthTablet: '72px',
  bottomBarHeightMobile: '64px',
  touchTargetMinPx: 44,
  fluidPadding: 'clamp(1rem, 3vw, 2rem)',
  fluidHeading: 'clamp(1.25rem, 2.5vw, 1.875rem)',
  fluidBody: 'clamp(1rem, 1.2vw, 1.125rem)',
};

