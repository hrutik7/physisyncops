"use client";

import { useEffect, useState } from "react";
import { Check, ChevronDown, FileSpreadsheet, X, Loader2 } from "lucide-react";
import { useOpentraStore } from "@/store/use-opentra-store";

export function MappingModal() {
  const open = useOpentraStore((state) => state.mappingOpen);
  const setOpen = useOpentraStore((state) => state.setMappingOpen);
  const suggestions = useOpentraStore((state) => state.mappingSuggestions);
  const uploadedColumns = useOpentraStore((state) => state.uploadedColumns);
  const confirmUpload = useOpentraStore((state) => state.confirmUpload);
  const loading = useOpentraStore((state) => state.loading);
  const taskStatus = useOpentraStore((state) => state.taskStatus);
  const taskMeta = useOpentraStore((state) => state.taskMeta);
  const error = useOpentraStore((state) => state.error);

  const [mappings, setMappings] = useState<Record<string, string>>({});

  // Initialize mappings with suggestions
  useEffect(() => {
    if (suggestions && suggestions.length > 0) {
      const initial: Record<string, string> = {};
      suggestions.forEach((s) => {
        if (s.uploadedColumn) {
          initial[s.canonicalField] = s.uploadedColumn;
        }
      });
      setMappings(initial);
    }
  }, [suggestions]);

  const handleSelectChange = (canonicalField: string, value: string) => {
    setMappings((prev) => ({
      ...prev,
      [canonicalField]: value
    }));
  };

  const handleSave = async () => {
    await confirmUpload(mappings);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full max-w-3xl overflow-hidden rounded-xl border border-[#e6e8f0] bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#e6e8f0] p-5">
          <div className="flex gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#f0ecfd] text-[#5b35d5]">
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#101426]">Confirm Column Mapping</h2>
              <p className="mt-1 text-sm text-[#68708a]">Fuzzy matching suggests canonical fields, then stores this template for Unigo Footwear.</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close mapping"
            title="Close mapping"
            onClick={() => setOpen(false)}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-[#e6e8f0] text-[#68708a] hover:bg-[#fbfaff]"
          >
            <X size={17} />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="rounded-lg border border-[#fde8e8] bg-[#fdf2f2] p-4 text-sm text-[#de2b25]">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-10 space-y-4">
              <Loader2 className="h-10 w-10 animate-spin text-[#5b35d5]" />
              <div className="text-center">
                <p className="font-semibold text-[#101426]">Processing Upload...</p>
                {taskStatus && (
                  <p className="text-xs text-[#68708a] mt-1">
                    Status: <span className="font-bold text-[#5b35d5]">{taskStatus}</span>
                    {taskMeta?.step && ` - ${taskMeta.step}`}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="rounded-lg border border-[#dbe7ff] bg-[#eef5ff] p-3.5 text-sm text-[#185be8]">
                First upload creates a baseline snapshot. Monitoring inferences begin after the next confirmed upload.
              </div>
              <div className="space-y-3">
                {suggestions.map((suggestion) => (
                  <div key={suggestion.canonicalField} className="grid gap-3 rounded-lg border border-[#e6e8f0] p-4 md:grid-cols-[180px_1fr_120px] md:items-center bg-[#fbfaff]">
                    <div>
                      <p className="text-sm font-semibold text-[#101426] capitalize">{suggestion.canonicalField.replace("_", " ")}</p>
                      <p className="mt-1 text-xs text-[#68708a]">{suggestion.required ? "Required" : "Optional"}</p>
                    </div>
                    <div className="relative">
                      <select
                        value={mappings[suggestion.canonicalField] ?? ""}
                        onChange={(e) => handleSelectChange(suggestion.canonicalField, e.target.value)}
                        className="h-10 w-full appearance-none rounded-lg border border-[#e6e8f0] bg-white px-3 pr-9 text-sm text-[#101426] focus:border-[#5b35d5] focus:outline-none"
                      >
                        <option value="">No mapping</option>
                        {uploadedColumns.map((column) => (
                          <option key={column} value={column}>
                            {column}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-3 text-[#68708a]" size={16} />
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="h-2 flex-1 rounded-full bg-[#edf0f6]">
                        <div className="h-2 rounded-full bg-[#0fb36b]" style={{ width: `${Math.round(suggestion.confidence * 100)}%` }} />
                      </div>
                      <span className="w-9 text-right text-xs font-bold text-[#68708a]">{Math.round(suggestion.confidence * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="flex flex-wrap justify-end gap-3 border-t border-[#e6e8f0] p-5">
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-lg border border-[#e6e8f0] px-4 py-2 text-sm font-medium text-[#172039] hover:bg-[#fbfaff]"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-[#5b35d5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4320c2] shadow-sm shadow-[#5b35d5]/20 disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
            Confirm & Save Template
          </button>
        </div>
      </div>
    </div>
  );
}
