import React, { useState } from 'react';
import { BottomSheet } from './BottomSheet';
import { Button } from './Button';
import { Input } from './Input';

export interface ConsentSheetProps {
  isOpen: boolean;
  onClose: () => void;
  caseTitle: string;
  onConfirmShare: (details: { recipientContact: string; scope: string; durationDays: number; permissions: string[] }) => void;
}

export const ConsentSheet: React.FC<ConsentSheetProps> = ({
  isOpen,
  onClose,
  caseTitle,
  onConfirmShare,
}) => {
  const [recipient, setRecipient] = useState('');
  const [durationDays, setDurationDays] = useState(30);
  const [includeNotes, setIncludeNotes] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirmShare({
      recipientContact: recipient,
      scope: includeNotes ? 'case_with_notes' : 'case_summary_docs',
      durationDays,
      permissions: ['view']
    });
  };

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="কী শেয়ার করবেন এবং কতদিনের জন্য, বেছে নিন">
      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div>
          <span className="text-xs font-semibold text-slate-500 block">শেয়ার করা হচ্ছে:</span>
          <span className="text-sm font-bold text-slate-900">{caseTitle}</span>
        </div>

        <Input
          label="আইনজীবী বা প্রাপকের মোবাইল নম্বর বা ইমেইল"
          placeholder="01XXXXXXXXX বা advocate@example.com"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          required
        />

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-slate-800">
            কতদিনের জন্য অ্যাক্সেস থাকবে? (স্বয়ংক্রিয়ভাবে মেয়াদ শেষ হবে)
          </label>
          <div className="flex gap-2">
            {[7, 15, 30, 90].map((days) => (
              <button
                key={days}
                type="button"
                onClick={() => setDurationDays(days)}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition ${
                  durationDays === days
                    ? 'bg-[#0B5D4B] text-white border-[#0B5D4B]'
                    : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                {days} দিন
              </button>
            ))}
          </div>
        </div>

        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs text-amber-900">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeNotes}
              onChange={(e) => setIncludeNotes(e.target.checked)}
              className="mt-0.5 rounded text-[#0B5D4B] focus:ring-[#0B5D4B]"
            />
            <span>আমার ব্যক্তিগত খসড়া নোট অন্তর্ভুক্ত করুন (সাধারণত এটি গোপন রাখা হয়)</span>
          </label>
        </div>

        <p className="text-[11px] text-slate-500 leading-normal">
          * অনুমতি যেকোনো মুহূর্তে ৬০ সেকেন্ডের মধ্যে প্রত্যাহার করা যাবে। প্রাপক ওটিপি (OTP) যাচাই ছাড়া এই নথি দেখতে পারবেন না।
        </p>

        <div className="pt-3 border-t flex justify-end gap-2">
          <Button variant="outline" type="button" onClick={onClose}>
            বাতিল
          </Button>
          <Button variant="primary" type="submit">
            নিশ্চিত ও শেয়ার করুন
          </Button>
        </div>
      </form>
    </BottomSheet>
  );
};
