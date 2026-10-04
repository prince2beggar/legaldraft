import React from 'react';

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'neutral' | 'primary' | 'attention' | 'urgent' | 'success';
  onRemove?: () => void;
}

export const Chip: React.FC<ChipProps> = ({
  children,
  variant = 'neutral',
  onRemove,
  className = '',
  ...props
}) => {
  const variants = {
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
    primary: "bg-[#E3F1EC] text-[#0B5D4B] border-[#0B5D4B]/30",
    attention: "bg-[#FFF3DC] text-[#C77D0A] border-[#C77D0A]/30",
    urgent: "bg-[#FDECEA] text-[#B3261E] border-[#B3261E]/30",
    success: "bg-emerald-50 text-emerald-800 border-emerald-200"
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="hover:opacity-75 focus:outline-none ml-0.5"
          aria-label="Remove"
        >
          ×
        </button>
      )}
    </span>
  );
};
