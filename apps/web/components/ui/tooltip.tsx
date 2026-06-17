"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export function Tooltip({
  content,
  children,
  side = "top",
  className,
  maxWidth = 280,
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
  maxWidth?: number;
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const id = useId();

  const updatePosition = () => {
    const trigger = triggerRef.current;
    if (!trigger) return;

    const rect = trigger.getBoundingClientRect();
    const gap = 8;

    switch (side) {
      case "top":
        setCoords({ top: rect.top - gap, left: rect.left + rect.width / 2 });
        break;
      case "bottom":
        setCoords({ top: rect.bottom + gap, left: rect.left + rect.width / 2 });
        break;
      case "left":
        setCoords({ top: rect.top + rect.height / 2, left: rect.left - gap });
        break;
      case "right":
        setCoords({ top: rect.top + rect.height / 2, left: rect.right + gap });
        break;
    }
  };

  useLayoutEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }
    updatePosition();
  }, [open, side]);

  useEffect(() => {
    if (!open) return;

    const onScrollOrResize = () => updatePosition();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, side]);

  const transform =
    side === "top"
      ? "translate(-50%, -100%)"
      : side === "bottom"
        ? "translate(-50%, 0)"
        : side === "left"
          ? "translate(-100%, -50%)"
          : "translate(0, -50%)";

  return (
    <span
      ref={triggerRef}
      className={cn("relative inline-flex", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined} className="inline-flex">
        {children}
      </span>
      {open && coords
        ? createPortal(
            <span
              id={id}
              role="tooltip"
              style={{ top: coords.top, left: coords.left, maxWidth, transform }}
              className="pointer-events-none fixed z-[9999] rounded-lg border border-[#e6e8f0] bg-[#101426] px-3 py-2 text-xs leading-5 text-white shadow-[0_12px_32px_rgba(16,20,38,0.24)]"
            >
              {content}
            </span>,
            document.body
          )
        : null}
    </span>
  );
}