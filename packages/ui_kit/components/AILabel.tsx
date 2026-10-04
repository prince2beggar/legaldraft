import React from 'react';

export interface AILabelProps {
  kind?: 'info' | 'analysis' | 'draft';
  className?: string;
}

export const AILabel: React.FC<AILabelProps> = ({ kind = 'analysis', className = '' }) => {
  const labels = {
    info: 'এআই তথ্য (AI Information)',
    analysis: 'এআই বিশ্লেষণ • আইনি পরামর্শ নয়',
    draft: 'এআই খসড়া (AI Draft)'
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-[#FFF3DC] text-[#7A4B00] border border-[#C77D0A]/30 select-none ${className}`}>
      <span aria-hidden="true">🤖</span>
      <span>{labels[kind]}</span>
    </span>
  );
};
