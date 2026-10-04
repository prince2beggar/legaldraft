import React from 'react';

export interface SourceChipProps {
  sourceTitle: string;
  sectionRef?: string;
  pageNo?: number;
  rights?: 'official' | 'licensed' | 'secondary';
  onClick?: () => void;
}

export const SourceChip: React.FC<SourceChipProps> = ({
  sourceTitle,
  sectionRef,
  pageNo,
  rights = 'official',
  onClick,
}) => {
  const icon = rights === 'official' ? '🏛️' : rights === 'licensed' ? '📜' : '📖';

  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#E3F1EC] text-[#0B5D4B] border border-[#0B5D4B]/30 hover:bg-[#D1E8E0] transition cursor-pointer"
      title={`${sourceTitle} ${sectionRef ? `(Section: ${sectionRef})` : ''}`}
    >
      <span aria-hidden="true">{icon}</span>
      <span className="truncate max-w-[180px]">{sourceTitle}</span>
      {sectionRef && <span className="text-[#08483A] font-bold">§{sectionRef}</span>}
      {pageNo && <span className="text-slate-500">p.{pageNo}</span>}
    </button>
  );
};
