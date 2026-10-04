import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'attention' | 'urgent' | 'soft';
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  className = '',
  ...props
}) => {
  const variants = {
    default: "bg-white border border-slate-200 shadow-sm",
    attention: "bg-[#FFF3DC] border border-[#C77D0A] text-[#7A4B00]",
    urgent: "bg-[#FDECEA] border border-[#B3261E] text-[#6D120D]",
    soft: "bg-[#E3F1EC] border border-[#0B5D4B]/20 text-[#0B5D4B]"
  };

  return (
    <div className={`rounded-xl p-4 sm:p-5 transition ${variants[variant]} ${className}`} {...props}>
      {children}
    </div>
  );
};
