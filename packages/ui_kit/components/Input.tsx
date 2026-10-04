import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5 text-left">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-slate-800">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`w-full min-h-[48px] px-3.5 py-2.5 rounded-xl border text-base text-slate-900 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0B5D4B] transition ${
          error ? 'border-red-500 focus:ring-red-500' : 'border-slate-300'
        } ${className}`}
        {...props}
      />
      {error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500">{helperText}</p>
      ) : null}
    </div>
  );
};
