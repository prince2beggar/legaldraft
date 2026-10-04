/**
 * AIN-AI AppShell Component (SRS Section 10.3, ADR-018)
 * Adaptive layout shell providing responsive navigation:
 * - Mobile (< 640px): Fixed bottom tab bar (5 tabs per SRS D8), min 44px touch targets.
 * - Tablet (640-1023px): Slim side rail with accessible tooltips.
 * - Desktop (>= 1024px): Full left sidebar with branding, Bangla labels, and profile info.
 * Enforces zero horizontal scroll, notch safe-areas, and fluid content boundaries.
 */

import React from 'react';
import { colors, layout, typography } from '../tokens';

export interface NavItem {
  id: string;
  labelBn: string;
  labelEn: string;
  icon: string;
  href: string;
  badge?: string;
  active?: boolean;
}

export interface AppShellProps {
  currentTab: string;
  lang?: 'bn' | 'en';
  userName?: string;
  userRole?: string;
  children: React.ReactNode;
  navItems?: NavItem[];
}

export const DEFAULT_NAV_ITEMS: NavItem[] = [
  { id: 'home', labelBn: 'হোম', labelEn: 'Home', icon: '🏠', href: '/' },
  { id: 'library', labelBn: 'আইন লাইব্রেরি', labelEn: 'Library', icon: '📚', href: '/library', badge: 'M10' },
  { id: 'cases', labelBn: 'মামলা', labelEn: 'Cases', icon: '📁', href: '/cases' },
  { id: 'drafts', labelBn: 'ড্রাফট ও টুলস', labelEn: 'Drafts', icon: '✍️', href: '/drafts' },
  { id: 'profile', labelBn: 'প্রোফাইল', labelEn: 'Profile', icon: '👤', href: '/me' },
];

export const AppShell: React.FC<AppShellProps> = ({
  currentTab,
  lang = 'bn',
  userName,
  userRole,
  children,
  navItems = DEFAULT_NAV_ITEMS,
}) => {
  return (
    <div className="ain-app-shell">
      {/* Desktop / Tablet Sidebar & Rail */}
      <aside className="ain-sidebar" aria-label="Primary Navigation">
        <div className="ain-brand">
          <span className="ain-brand-logo" aria-hidden="true">⚖️</span>
          <div className="ain-brand-text">
            <span className="ain-brand-title">আইন-AI</span>
            <span className="ain-brand-subtitle">Bangladesh Legal OS</span>
          </div>
        </div>

        <nav className="ain-nav-list" role="navigation">
          {navItems.map((item) => {
            const isActive = item.id === currentTab;
            const label = lang === 'bn' ? item.labelBn : item.labelEn;
            return (
              <a
                key={item.id}
                href={item.href}
                className={`ain-nav-item ${isActive ? 'active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                title={label}
              >
                <span className="ain-nav-icon" aria-hidden="true">{item.icon}</span>
                <span className="ain-nav-label">{label}</span>
                {item.badge && <span className="ain-nav-badge">{item.badge}</span>}
              </a>
            );
          })}
        </nav>

        {userName && (
          <div className="ain-user-card">
            <div className="ain-user-avatar" aria-hidden="true">👤</div>
            <div className="ain-user-info">
              <span className="ain-user-name">{userName}</span>
              <span className="ain-user-role">{userRole || 'Citizen'}</span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="ain-main-viewport" id="main-content">
        <div className="ain-content-inner">
          {children}
        </div>
      </main>

      {/* Mobile Bottom Tab Bar (< 640px) */}
      <nav className="ain-bottom-nav" aria-label="Mobile Navigation">
        {navItems.map((item) => {
          const isActive = item.id === currentTab;
          const label = lang === 'bn' ? item.labelBn : item.labelEn;
          return (
            <a
              key={item.id}
              href={item.href}
              className={`ain-bottom-tab ${isActive ? 'active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="ain-tab-icon" aria-hidden="true">{item.icon}</span>
              <span className="ain-tab-label">{label}</span>
            </a>
          );
        })}
      </nav>

      {/* Embedded CSS for Cross-Platform Responsive Parity */}
      <style>{`
        .ain-app-shell {
          display: flex;
          min-height: 100vh;
          min-height: 100dvh;
          background-color: ${colors.neutral.bg};
          color: ${colors.neutral.textMain};
          font-family: ${typography.fontFamilyBangla};
          overflow-x: hidden;
          width: 100%;
        }

        /* Desktop Sidebar (>= 1024px) */
        .ain-sidebar {
          display: flex;
          flex-direction: column;
          width: ${layout.sidebarWidthDesktop};
          background-color: #ffffff;
          border-right: 1px solid ${colors.neutral.border};
          position: sticky;
          top: 0;
          height: 100vh;
          height: 100dvh;
          padding: 1.25rem 1rem;
          flex-shrink: 0;
          z-index: 40;
          transition: width 0.2s ease;
        }

        .ain-brand {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding-bottom: 1.5rem;
          border-bottom: 1px solid ${colors.neutral.border};
          margin-bottom: 1rem;
        }

        .ain-brand-logo {
          font-size: 1.75rem;
          line-height: 1;
        }

        .ain-brand-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: ${colors.primary};
          display: block;
        }

        .ain-brand-subtitle {
          font-size: 0.75rem;
          color: ${colors.neutral.textMuted};
          display: block;
        }

        .ain-nav-list {
          display: flex;
          flex-direction: column;
          gap: 0.375rem;
          flex: 1;
        }

        .ain-nav-item {
          display: flex;
          align-items: center;
          gap: 0.875rem;
          padding: 0.75rem 1rem;
          min-height: ${layout.touchTargetMinPx}px;
          border-radius: 8px;
          color: ${colors.neutral.textMain};
          text-decoration: none;
          font-size: 0.95rem;
          font-weight: 500;
          transition: background-color 0.15s ease, color 0.15s ease;
        }

        .ain-nav-item:hover, .ain-nav-item:focus-visible {
          background-color: ${colors.primarySoft};
          color: ${colors.primary};
          outline: 2px solid ${colors.primary};
          outline-offset: -2px;
        }

        .ain-nav-item.active {
          background-color: ${colors.primary};
          color: #ffffff;
          font-weight: 600;
        }

        .ain-nav-icon {
          font-size: 1.25rem;
          flex-shrink: 0;
        }

        .ain-nav-label {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .ain-nav-badge {
          margin-left: auto;
          font-size: 0.7rem;
          padding: 0.15rem 0.4rem;
          border-radius: 9999px;
          background-color: ${colors.primarySoft};
          color: ${colors.primary};
        }

        .ain-nav-item.active .ain-nav-badge {
          background-color: rgba(255, 255, 255, 0.25);
          color: #ffffff;
        }

        .ain-user-card {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          border-top: 1px solid ${colors.neutral.border};
          margin-top: auto;
        }

        .ain-user-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background-color: ${colors.primarySoft};
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.1rem;
        }

        .ain-user-info {
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .ain-user-name {
          font-size: 0.875rem;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .ain-user-role {
          font-size: 0.75rem;
          color: ${colors.neutral.textMuted};
          text-transform: capitalize;
        }

        /* Main Viewport */
        .ain-main-viewport {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
          overflow-y: auto;
        }

        .ain-content-inner {
          flex: 1;
          padding: ${layout.fluidPadding};
          max-width: ${layout.containerMaxWidth};
          margin: 0 auto;
          width: 100%;
          box-sizing: border-box;
        }

        /* Mobile Bottom Tab Bar (Hidden on >= 640px) */
        .ain-bottom-nav {
          display: none;
        }

        /* Tablet Breakpoint (640px to 1023px) - Slim Side Rail */
        @media (min-width: 640px) and (max-width: 1023px) {
          .ain-sidebar {
            width: ${layout.sidebarWidthTablet};
            padding: 1rem 0.5rem;
            align-items: center;
          }

          .ain-brand-text,
          .ain-nav-label,
          .ain-nav-badge,
          .ain-user-info {
            display: none;
          }

          .ain-brand {
            padding-bottom: 1rem;
            margin-bottom: 1rem;
            justify-content: center;
          }

          .ain-nav-item {
            justify-content: center;
            padding: 0.75rem 0;
            width: 100%;
          }

          .ain-user-card {
            justify-content: center;
            padding: 0.5rem 0;
          }
        }

        /* Mobile Breakpoint (< 640px) */
        @media (max-width: 639px) {
          .ain-sidebar {
            display: none;
          }

          .ain-app-shell {
            padding-bottom: calc(${layout.bottomBarHeightMobile} + env(safe-area-inset-bottom, 0px));
          }

          .ain-content-inner {
            padding: 1rem;
          }

          .ain-bottom-nav {
            display: flex;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: ${layout.bottomBarHeightMobile};
            background-color: #ffffff;
            border-top: 1px solid ${colors.neutral.border};
            z-index: 50;
            padding-bottom: env(safe-area-inset-bottom, 0px);
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
          }

          .ain-bottom-tab {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: ${layout.touchTargetMinPx}px;
            color: ${colors.neutral.textMuted};
            text-decoration: none;
            gap: 2px;
            font-size: 0.75rem;
            font-weight: 500;
            touch-action: manipulation;
          }

          .ain-bottom-tab:hover, .ain-bottom-tab:focus-visible {
            color: ${colors.primary};
          }

          .ain-bottom-tab.active {
            color: ${colors.primary};
            font-weight: 700;
          }

          .ain-tab-icon {
            font-size: 1.25rem;
            line-height: 1;
          }

          .ain-tab-label {
            font-size: 0.75rem;
            line-height: 1.1;
          }
        }
      `}</style>
    </div>
  );
};
