"use client";

import {
  BarChart3,
  Bell,
  Bot,
  Boxes,
  FileText,
  HeartPulse,
  Megaphone,
  Network,
  Settings,
  Shuffle,
  Users,
  Zap,
  Trash2,
  Database
} from "lucide-react";
import { cn } from "@/lib/utils";

import { useOpentraStore } from "@/store/use-opentra-store";

export function Sidebar() {
  const decisions = useOpentraStore((state) => state.decisions);
  const pendingCount = decisions.filter((d) => d.state === "pending").length;
  const resetDatabase = useOpentraStore((state) => state.resetDatabase);
  const snapshots = useOpentraStore((state) => state.snapshots);
  const activeView = useOpentraStore((state) => state.activeView);
  const setActiveView = useOpentraStore((state) => state.setActiveView);
  const brandName = useOpentraStore((state) => state.brandName);

  const navItems = [
    { label: "Decision Feed", icon: Zap, active: activeView === "Decision Feed", count: decisions.length },
    { label: "Data Sandbox", icon: Database, active: activeView === "Data Sandbox" },
    { label: "Health Overview", icon: HeartPulse, active: activeView === "Health Overview" },
    // { label: "Performance", icon: BarChart3, active: activeView === "Performance" },
    // { label: "Inventory", icon: Boxes, active: activeView === "Inventory" },
    // { label: "Marketing", icon: Megaphone, active: activeView === "Marketing" },
    // { label: "Customers", icon: Users, active: activeView === "Customers" },
    // { label: "Alerts", icon: Bell, active: activeView === "Alerts", count: pendingCount },
    // { label: "Reports", icon: FileText, active: activeView === "Reports" },
    // { label: "Outcomes", icon: Shuffle, active: activeView === "Outcomes" },
    // { label: "Settings", icon: Settings, active: activeView === "Settings" }
  ];

  return (
    <aside className="hidden h-screen border-r border-[#ebe8f5] bg-[#faf9ff] px-4 py-5 lg:flex lg:flex-col">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#5b35d5] text-white">
          <Network size={18} />
        </div>
        <span className="text-lg font-semibold text-[#101426]">Unigo Operator</span>
      </div>

      <nav className="mt-10 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              type="button"
              onClick={() => setActiveView(item.label)}
              className={cn(
                "flex h-12 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium text-[#172039] transition",
                item.active ? "bg-[#efebff] text-[#4320c2]" : "hover:bg-white"
              )}
            >
              <Icon size={18} />
              <span className="min-w-0 flex-1 text-left">{item.label}</span>
              {item.count && item.count > 0 ? (
                <span className="grid h-6 min-w-6 place-items-center rounded-full bg-[#dfd7ff] px-2 text-xs text-[#4320c2]">{item.count}</span>
              ) : null}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto space-y-4">
        <div className="rounded-lg border border-[#ebe8f5] bg-white p-3">
          <div className="flex items-center gap-3 border-b border-[#ebe8f5] pb-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#111322] text-sm font-bold text-white">
              {brandName.substring(0, 2).toLowerCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#101426]">{brandName}</p>
              <p className="text-xs text-[#68708a]">D2C Brand</p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-[#f0eff6] text-xs font-semibold text-[#101426]">HK</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#101426]">Hruvik</p>
              <p className="text-xs text-[#68708a]">Founder</p>
            </div>
          </div>
        </div>

        {snapshots.length > 0 && (
          <button
            type="button"
            onClick={() => resetDatabase()}
            className="flex w-full items-center gap-3 rounded-lg border border-[#ffd9d7] bg-[#fff1f0] p-3 text-left text-[#de2b25] transition hover:bg-[#ffe8e7]"
          >
            <div className="grid h-10 w-10 place-items-center rounded-full bg-[#fde8e8]">
              <Trash2 size={19} />
            </div>
            <div>
              <p className="text-sm font-semibold">Reset Database</p>
              <p className="text-xs text-[#a84c48]">Clear uploaded state</p>
            </div>
          </button>
        )}

        <button type="button" className="flex w-full items-center gap-3 rounded-lg border border-[#ebe8f5] bg-white p-3 text-left">
          <div className="grid h-10 w-10 place-items-center rounded-full bg-[#efebff] text-[#4320c2]">
            <Bot size={19} />
          </div>
          <div>
            <p className="text-sm font-semibold text-[#101426]">Need help?</p>
            <p className="text-xs text-[#68708a]">Talk to Opentra AI</p>
          </div>
        </button>
      </div>
    </aside>
  );
}
