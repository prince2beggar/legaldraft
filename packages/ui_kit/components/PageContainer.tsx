/**
 * AIN-AI PageContainer Component (ADR-018)
 * Fluid page container providing consistent margins, clamp padding, and zero horizontal scroll.
 */

import React from 'react';
import { layout } from '../tokens';

export interface PageContainerProps {
  children: React.ReactNode;
  maxWidth?: string;
  className?: string;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  maxWidth = layout.containerMaxWidth,
  className = '',
}) => {
  return (
    <div className={`ain-page-container ${className}`} style={{ maxWidth }}>
      {children}
      <style>{`
        .ain-page-container {
          width: 100%;
          margin: 0 auto;
          box-sizing: border-box;
          overflow-x: hidden;
        }
      `}</style>
    </div>
  );
};
