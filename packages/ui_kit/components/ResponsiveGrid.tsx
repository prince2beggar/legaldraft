/**
 * AIN-AI ResponsiveGrid Component (ADR-018)
 * Fluid CSS Grid that automatically adapts columns:
 * - Mobile (< 640px): 1 column
 * - Tablet (640-1023px): 2 columns
 * - Desktop (>= 1024px): 3 columns (configurable)
 */

import React from 'react';

export interface ResponsiveGridProps {
  children: React.ReactNode;
  columnsDesktop?: number;
  columnsTablet?: number;
  gap?: string;
  className?: string;
}

export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  columnsDesktop = 3,
  columnsTablet = 2,
  gap = '1.25rem',
  className = '',
}) => {
  return (
    <div className={`ain-responsive-grid ${className}`}>
      {children}
      <style>{`
        .ain-responsive-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: ${gap};
          width: 100%;
          box-sizing: border-box;
        }

        @media (min-width: 640px) and (max-width: 1023px) {
          .ain-responsive-grid {
            grid-template-columns: repeat(${columnsTablet}, minmax(0, 1fr));
          }
        }

        @media (min-width: 1024px) {
          .ain-responsive-grid {
            grid-template-columns: repeat(${columnsDesktop}, minmax(0, 1fr));
          }
        }
      `}</style>
    </div>
  );
};
