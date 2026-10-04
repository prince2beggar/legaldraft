import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'urgent' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}) => {
  const base = "inline-flex items-center justify-center font-medium rounded-xl transition focus:outline-none focus:ring-2 focus:ring-offset-2 min-h-[48px] px-4 py-2.5 text-base";
  
  const variants = {
    primary: "bg-[#0B5D4B] text-white hover:bg-[#08483A] focus:ring-[#0B5D4B] shadow-sm",
    secondary: "bg-[#E3F1EC] text-[#0B5D4B] hover:bg-[#D1E8E0] focus:ring-[#0B5D4B]",
    outline: "border border-slate-300 text-slate-700 hover:bg-slate-50 focus:ring-slate-400 bg-white",
    urgent: "bg-[#B3261E] text-white hover:bg-[#8F1E17] focus:ring-[#B3261E] shadow-sm",
    ghost: "text-slate-600 hover:bg-slate-100 focus:ring-slate-300"
  };

  const sizes = {
    sm: "min-h-[40px] text-sm px-3 py-1.5",
    md: "min-h-[48px] text-base px-4 py-2.5",
    lg: "min-h-[56px] text-lg px-6 py-3"
  };

  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  );
};
