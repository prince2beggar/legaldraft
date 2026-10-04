import React from 'react';

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  children,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:p-4">
      <div 
        className="fixed inset-0" 
        onClick={onClose} 
        aria-hidden="true" 
      />
      <div className="relative w-full max-w-lg rounded-t-2xl sm:rounded-2xl bg-white p-6 shadow-xl max-h-[85vh] overflow-y-auto animate-in slide-in-from-bottom duration-200">
        <div className="mx-auto w-12 h-1.5 rounded-full bg-slate-300 mb-4 sm:hidden" />
        {title && (
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <h3 className="text-lg font-bold text-slate-900">{title}</h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        )}
        <div>{children}</div>
      </div>
    </div>
  );
};
