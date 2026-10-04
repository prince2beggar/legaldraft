import React, { useState } from 'react';
import { Button } from './Button';

export interface NextActionCardProps {
  caseTitle?: string;
  actionText: string;
  daysLeft?: number;
  buttonLabel?: string;
  reasonRefs?: string[];
  onAction?: () => void;
}

export const NextActionCard: React.FC<NextActionCardProps> = ({
  caseTitle,
  actionText,
  daysLeft,
  buttonLabel = "পদক্ষেপ নিন",
  reasonRefs = [],
  onAction,
}) => {
  const [showReason, setShowReason] = useState(false);

  return (
    <div className="rounded-xl p-5 bg-[#FFF3DC] border-2 border-[#C77D0A] shadow-sm text-left">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-[#7A4B00] uppercase tracking-wide flex items-center gap-1.5">
          <span>⚡</span>
          <span>এরপর আপনার করণীয়</span>
        </span>
        {caseTitle && (
          <span className="text-xs bg-white/70 px-2.5 py-0.5 rounded-full font-medium text-slate-700">
            {caseTitle}
          </span>
        )}
      </div>

      <h3 className="text-lg font-bold text-slate-900 mb-2">
        {actionText}
      </h3>

      {daysLeft !== undefined && (
        <p className="text-xs font-semibold text-[#7A4B00] mb-3">
          {daysLeft < 0 ? `সময়সীমা অতিক্রান্ত (${Math.abs(daysLeft)} দিন)` : `${daysLeft} দিন সময় রয়েছে`}
        </p>
      )}

      <div className="flex items-center justify-between gap-3 mt-4">
        {onAction && (
          <Button variant="primary" onClick={onAction} className="min-w-[140px]">
            {buttonLabel}
          </Button>
        )}

        {reasonRefs.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setShowReason(!showReason)}
              className="text-xs text-slate-600 hover:text-slate-900 underline font-medium"
            >
              কেন এই পরামর্শ?
            </button>
          </div>
        )}
      </div>

      {showReason && reasonRefs.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#C77D0A]/30 text-xs text-slate-700">
          <p className="font-semibold mb-1">কারণসমূহ:</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {reasonRefs.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
