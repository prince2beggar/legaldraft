import React from 'react';

export interface ToastProps {
  message: string;
  type?: 'info' | 'success' | 'warning' | 'error';
  onDismiss?: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  onDismiss,
}) => {
  const types = {
    info: 'bg-slate-900 text-white',
    success: 'bg-[#0B5D4B] text-white',
    warning: 'bg-[#C77D0A] text-white',
    error: 'bg-[#B3261E] text-white',
  };

  return (
    <div className={`fixed bottom-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium ${types[type]} transition animate-in fade-in`}>
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="text-white/80 hover:text-white font-bold ml-2">
          ✕
        </button>
      )}
    </div>
  );
};
