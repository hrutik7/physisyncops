"use client";

import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function DeleteDecisionButton({
  onDelete,
  compact = false,
  className,
}: {
  onDelete: () => void | Promise<void>;
  compact?: boolean;
  className?: string;
}) {
  const handleClick = async () => {
    const confirmed = window.confirm(
      "Delete this decision permanently? This removes it from the feed and cannot be undone."
    );
    if (!confirmed) return;
    await onDelete();
  };

  if (compact) {
    return (
      <button
        type="button"
        aria-label="Delete decision"
        title="Delete decision"
        onClick={handleClick}
        className={cn(
          "grid h-8 w-8 place-items-center rounded-lg text-[#68708a] transition-colors hover:bg-[#fff1f0] hover:text-[#de2b25]",
          className
        )}
      >
        <Trash2 size={18} />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border border-[#fde8e8] bg-white px-3 py-2 text-sm font-semibold text-[#de2b25] transition hover:bg-[#fff1f0]",
        className
      )}
    >
      <Trash2 size={15} />
      Delete
    </button>
  );
}