import { cn } from "@/lib/utils";
import { Severity, DecisionState } from "@/lib/types";

const severityClass: Record<Severity, string> = {
  high: "border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]",
  medium: "border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]",
  low: "border-[#c8f3df] bg-[#ecfff6] text-[#07824b]"
};

const stateClass: Record<DecisionState, string> = {
  pending: "border-[#e8ebf2] bg-[#f7f8fb] text-[#68708a]",
  monitoring: "border-[#dbe7ff] bg-[#eef5ff] text-[#185be8]",
  verified: "border-[#d8f2e6] bg-[#ecfff6] text-[#07824b]",
  successful: "border-[#d8f2e6] bg-[#ecfff6] text-[#07824b]",
  unsuccessful: "border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]",
  ignored: "border-[#e8ebf2] bg-[#f7f8fb] text-[#68708a]",
  snoozed: "border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]"
};

export function Pill({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium", className)}>{children}</span>;
}

export function SeverityPill({ severity }: { severity: Severity }) {
  return <Pill className={severityClass[severity]}>{severity.toUpperCase()}</Pill>;
}

export function StatePill({ state }: { state: DecisionState }) {
  return <Pill className={stateClass[state]}>{state.replace("_", " ").toUpperCase()}</Pill>;
}

export function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="min-w-[128px]">
      <div className="mb-1 flex items-center justify-between text-xs text-muted">
        <span>Confidence</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div className="h-2 rounded-full bg-line">
        <div className="h-2 rounded-full bg-ink" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
    </div>
  );
}

export function IconButton({
  children,
  label,
  onClick,
  active
}: {
  children: React.ReactNode;
  label: string;
  onClick?: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={cn(
        "grid h-9 w-9 place-items-center rounded-md border border-line bg-white text-graphite transition hover:border-ink hover:text-ink",
        active && "border-ink bg-ink text-white hover:text-white"
      )}
    >
      {children}
    </button>
  );
}
