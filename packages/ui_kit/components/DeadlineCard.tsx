import React, { useState } from 'react';
import { Button } from './Button';

export interface DeadlineCardProps {
  title: string;
  dueDate: string;
  daysLeft: number;
  calcSteps?: string[];
  isConfirmed?: boolean;
  onConfirm?: () => void;
  onSetOwnDate?: () => void;
}

export const DeadlineCard: React.FC<DeadlineCardProps> = ({
  title,
  dueDate,
  daysLeft,
  calcSteps = [],
  isConfirmed = false,
  onConfirm,
  onSetOwnDate,
}) => {
  const [showSteps, setShowSteps] = useState(false);
  const isUrgent = daysLeft <= 3 && !isConfirmed;

  return (
    <div className={`rounded-xl p-4 border transition ${
      isUrgent ? 'bg-[#FDECEA] border-[#B3261E]' : 'bg-[#FFF3DC] border-[#C77D0A]'
    }`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">জরুরি সময়সীমা</span>
          <h4 className="text-base font-bold text-slate-900">{title}</h4>
        </div>
        <div className="text-right">
          <span className="text-lg font-extrabold text-slate-900 block">{dueDate}</span>
          <span className={`text-xs font-bold ${daysLeft < 0 ? 'text-red-700' : 'text-[#C77D0A]'}`}>
            {daysLeft < 0 ? `${Math.abs(daysLeft)} দিন পার হয়েছে` : `${daysLeft} দিন বাকি`}
          </span>
        </div>
      </div>

      {calcSteps.length > 0 && (
        <div className="mt-2 text-xs">
          <button
            type="button"
            onClick={() => setShowSteps(!showSteps)}
            className="text-slate-600 hover:text-slate-900 underline font-medium"
          >
            {showSteps ? 'গণনার পদ্ধতি লুকান ▲' : 'কীভাবে গণনা করা হয়েছে ▼'}
          </button>
          {showSteps && (
            <ul className="mt-2 pl-4 list-disc space-y-1 text-slate-700 bg-white/60 p-2.5 rounded-lg border border-amber-200">
              {calcSteps.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {!isConfirmed && onConfirm && (
          <Button size="sm" variant="primary" onClick={onConfirm}>
            তারিখটি নিশ্চিত করুন
          </Button>
        )}
        {onSetOwnDate && (
          <Button size="sm" variant="outline" onClick={onSetOwnDate}>
            আমার নিজস্ব তারিখ নির্ধারণ করব
          </Button>
        )}
      </div>
    </div>
  );
};
