"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export function Popover({
  trigger,
  content,
  align = "end",
  className,
  panelClassName,
}: {
  trigger: ReactNode;
  content: ReactNode;
  align?: "start" | "center" | "end";
  className?: string;
  panelClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number; transform: string } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const id = useId();

  const updatePosition = () => {
    const triggerEl = triggerRef.current;
    if (!triggerEl) return;

    const rect = triggerEl.getBoundingClientRect();
    const gap = 8;
    const top = rect.bottom + gap;

    let left = rect.left;
    let transform = "none";

    if (align === "center") {
      left = rect.left + rect.width / 2;
      transform = "translateX(-50%)";
    } else if (align === "end") {
      left = rect.right;
      transform = "translateX(-100%)";
    }

    setCoords({ top, left, transform });
  };

  useLayoutEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }
    updatePosition();
  }, [open, align]);

  useEffect(() => {
    if (!open) return;

    const onScrollOrResize = () => updatePosition();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, align]);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  return (
    <div className={cn("relative inline-flex", className)}>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex"
      >
        {trigger}
      </button>
      {open && coords
        ? createPortal(
            <div
              ref={panelRef}
              id={id}
              role="dialog"
              style={{ top: coords.top, left: coords.left, transform: coords.transform }}
              className={cn(
                "fixed z-[9999] min-w-[280px] rounded-xl border border-[#e6e8f0] bg-white p-4 shadow-[0_20px_60px_rgba(38,35,64,0.12)]",
                panelClassName
              )}
            >
              {content}
            </div>,
            document.body
          )
        : null}
    </div>
  );
}