import React from 'react';

export interface StatusBadgeProps {
  state: 'extracted' | 'reviewed' | 'verified';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state }) => {
  const configs = {
    extracted: {
      text: 'এআই পড়েছে, আপনি মিলিয়ে দেখুন',
      className: 'bg-[#FFF3DC] text-[#7A4B00] border border-[#C77D0A]/30',
      icon: '⚙'
    },
    reviewed: {
      text: 'আপনি যাচাই করেছেন',
      className: 'bg-white text-[#0B5D4B] border-2 border-[#0B5D4B]',
      icon: '✓'
    },
    verified: {
      text: 'অনুমোদিত ব্যক্তি যাচাই করেছেন',
      className: 'bg-[#0B5D4B] text-white border border-[#0B5D4B]',
      icon: '🛡'
    }
  };

  const c = configs[state];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${c.className}`}>
      <span aria-hidden="true">{c.icon}</span>
      <span>{c.text}</span>
    </span>
  );
};
