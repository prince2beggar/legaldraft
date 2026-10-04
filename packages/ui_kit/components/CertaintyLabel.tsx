import React from 'react';

export interface CertaintyLabelProps {
  level: 'clear' | 'check' | 'not_sure';
}

export const CertaintyLabel: React.FC<CertaintyLabelProps> = ({ level }) => {
  const configs = {
    clear: {
      text: 'স্পষ্ট ও নির্ভরযোগ্য সূত্রে প্রমাণিত',
      bg: 'bg-emerald-50',
      textColor: 'text-emerald-800',
      border: 'border-emerald-200',
      icon: '✓'
    },
    check: {
      text: 'যাচাই সাপেক্ষ',
      bg: 'bg-[#FFF3DC]',
      textColor: 'text-[#7A4B00]',
      border: 'border-[#C77D0A]/30',
      icon: '⚠'
    },
    not_sure: {
      text: 'নিশ্চিত নয় • আইনজীবীকে জিজ্ঞাসা করুন',
      bg: 'bg-[#FDECEA]',
      textColor: 'text-[#6D120D]',
      border: 'border-[#B3261E]/30',
      icon: '?'
    }
  };

  const c = configs[level];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${c.bg} ${c.textColor} ${c.border}`}>
      <span aria-hidden="true">{c.icon}</span>
      <span>{c.text}</span>
    </span>
  );
};
