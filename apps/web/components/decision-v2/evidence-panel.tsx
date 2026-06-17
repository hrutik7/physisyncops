"use client";

import { Check, X } from "lucide-react";
import { EvidenceRequired } from "@/lib/types";

function EvidenceList({ title, items, available }: { title: string; items: string[]; available: boolean }) {
  if (!items.length) return null;

  return (
    <div>
      <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#68708a]">{title}</p>
      <ul className="mt-2 space-y-2">
        {items.map((label) => (
          <li key={label} className="flex items-center justify-between rounded-lg border border-[#edf0f6] px-3 py-2 text-sm">
            <span className="font-medium text-[#303954]">{label}</span>
            {available ? (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-[#07824b]">
                <Check size={14} /> Available
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-[#de2b25]">
                <X size={14} /> Missing
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EvidencePanel({ evidence }: { evidence: EvidenceRequired }) {
  const available = evidence.requirements.filter((item) => item.available).map((item) => item.label);
  const missing = evidence.requirements.filter((item) => !item.available).map((item) => item.label);

  return (
    <section className="rounded-xl border border-[#edf0f6] bg-white p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Evidence Required</h4>
      <p className="mt-1 text-xs text-[#68708a]">What we have versus what is still needed to verify this decision.</p>

      <div className="mt-4 space-y-4">
        <EvidenceList title="Evidence Available" items={available} available />
        <EvidenceList title="Evidence Missing" items={missing} available={false} />
      </div>

      <p className="mt-4 rounded-lg border border-dashed border-[#e6e8f0] bg-[#fbfaff] px-3 py-2 text-xs text-[#68708a]">
        {evidence.allRequiredAvailable ? evidence.disclaimer : `If unavailable: ${evidence.disclaimer}`}
      </p>
    </section>
  );
}