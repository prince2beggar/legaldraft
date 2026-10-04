import React from 'react';
import { Button } from './Button';

export interface EmergencyContact {
  name: string;
  number: string;
  description?: string;
  verifiedAt?: string;
}

export interface UrgentBannerProps {
  contacts?: EmergencyContact[];
  onQuickExit?: () => void;
  onContinue?: () => void;
}

export const UrgentBanner: React.FC<UrgentBannerProps> = ({
  contacts = [],
  onQuickExit,
  onContinue,
}) => {
  return (
    <div className="rounded-xl p-5 bg-[#FDECEA] border-2 border-[#B3261E] text-slate-900 mb-6 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[#B3261E]">
          <span className="text-xl" aria-hidden="true">🚨</span>
          <h3 className="text-base font-bold">এটি জরুরি হতে পারে। এখনই সাহায্য নিন।</h3>
        </div>
        {onQuickExit && (
          <button
            onClick={onQuickExit}
            className="text-xs bg-[#B3261E] text-white px-2.5 py-1 rounded font-semibold hover:bg-[#8F1E17] transition"
          >
            দ্রুত প্রস্থান (Quick Exit)
          </button>
        )}
      </div>

      <p className="text-xs text-slate-700 mb-4 leading-relaxed">
        গ্রেপ্তার, পারিবারিক সহিংসতা, শারীরিক হুমকি বা তাৎক্ষণিক উচ্ছেদের পরিস্থিতিতে সাধারণ পরামর্শের অপেক্ষা না করে সরাসরি আইনজীবী বা আইনি সহায়তা সংস্থার সাথে যোগাযোগ করুন।
      </p>

      {contacts.length > 0 && (
        <div className="space-y-2 mb-4">
          <span className="text-xs font-bold text-[#6D120D] block uppercase">জরুরি হেল্পলাইন নম্বর:</span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {contacts.map((c, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-white border border-red-200 text-xs">
                <span className="font-bold text-slate-900 block">{c.name}</span>
                <span className="text-sm font-extrabold text-[#B3261E] block my-0.5">{c.number}</span>
                {c.description && <span className="text-slate-500 block text-[11px]">{c.description}</span>}
                {c.verifiedAt && <span className="text-[10px] text-emerald-700 block mt-1">✓ যাচাইকৃত: {c.verifiedAt}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {onContinue && (
        <div className="pt-2 border-t border-red-200 flex justify-end">
          <Button size="sm" variant="outline" onClick={onContinue}>
            পরিস্থিতি অবগত আছি, এগিয়ে চলুন →
          </Button>
        </div>
      )}
    </div>
  );
};
