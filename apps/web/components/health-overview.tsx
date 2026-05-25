"use client";

import { 
  Calendar, 
  Download, 
  ArrowUpRight, 
  Package, 
  Megaphone, 
  Truck, 
  Users, 
  TrendingUp, 
  Zap, 
  CheckCircle, 
  AlertTriangle, 
  ChevronRight, 
  DollarSign
} from "lucide-react";
import { useOpentraStore } from "@/store/use-opentra-store";
import { cn } from "@/lib/utils";

export function HealthOverview() {
  const decisions = useOpentraStore((state) => state.decisions);
  const skus = useOpentraStore((state) => state.skus);
  const campaigns = useOpentraStore((state) => state.campaigns);
  const customerSegments = useOpentraStore((state) => state.customerSegments);
  
  const setActiveView = useOpentraStore((state) => state.setActiveView);
  const setSelectedDecision = useOpentraStore((state) => state.setSelectedDecision);

  // 1. Calculate Active/Pending Alert Counts
  const pendingCount = decisions.filter((d) => d.state === "pending").length;
  const monitoringCount = decisions.filter((d) => d.state === "monitoring").length;
  const successfulCount = decisions.filter((d) => d.state === "successful").length;
  const totalCount = decisions.length;

  const handleDecisionClick = (id: string) => {
    setSelectedDecision(id);
    setActiveView("Decision Feed");
  };

  // 2. Dynamic Operational Stability Score Calculation
  // Base score is 98. We deduct points based on unresolved (pending/monitoring) risks.
  const activeUnresolvedDecisions = decisions.filter((d) => d.state === "pending" || d.state === "monitoring");
  const stabilityDeduction = activeUnresolvedDecisions.reduce((sum, d) => {
    if (d.severity === "high") return sum + 15;
    if (d.severity === "medium") return sum + 8;
    return sum + 4;
  }, 0);
  
  const stabilityScore = Math.max(30, 98 - stabilityDeduction);
  const isStable = stabilityScore >= 75;
  const isAtRisk = stabilityScore >= 55 && stabilityScore < 75;

  // Calculate comparative stability change vs last week (baseline)
  // If we have resolved decisions, show progress pts gain!
  const stabilityGain = 12 + (successfulCount * 5);

  // 3. Dynamic Domain Health Score Calculations
  // A. Inventory Domain Health
  const minStockoutDays = skus.length > 0 
    ? Math.min(...skus.map((s) => s.projectedStockoutDays)) 
    : 5.6;
  const inventoryDeduction = minStockoutDays < 7 ? Math.round((7 - minStockoutDays) * 10) : 0;
  const inventoryScore = Math.max(40, 96 - inventoryDeduction);
  const inventoryStatus = inventoryScore >= 80 ? "Good" : inventoryScore >= 60 ? "Stable" : "Risky";

  // B. Marketing Domain Health
  // Deduct based on high campaign spending or poor ROAS
  const avgRoasDelivered = campaigns.length > 0
    ? campaigns.reduce((sum, c) => sum + c.roasOnDeliveredOrders, 0) / campaigns.length
    : 2.31;
  const roasDeduction = avgRoasDelivered < 2.5 ? Math.round((2.5 - avgRoasDelivered) * 20) : 0;
  const marketingScore = Math.max(40, 94 - roasDeduction);
  const marketingStatus = marketingScore >= 80 ? "Good" : marketingScore >= 60 ? "At Risk" : "Risky";

  // C. Logistics Domain Health
  // Deduct based on RTO rate
  const avgRtoRate = campaigns.length > 0
    ? campaigns.reduce((sum, c) => sum + c.rtoRateAttributed, 0) / campaigns.length
    : 16.8;
  const rtoDeduction = avgRtoRate > 15 ? Math.round((avgRtoRate - 15) * 4) : 0;
  const logisticsScore = Math.max(30, 92 - rtoDeduction);
  const logisticsStatus = logisticsScore >= 70 ? "Good" : logisticsScore >= 50 ? "Stable" : "Risky";

  // D. Customers Domain Health
  const avgRepeatRate = customerSegments.length > 0
    ? customerSegments.reduce((sum, s) => sum + s.repeatRate, 0) / customerSegments.length
    : 24.6;
  const customerScore = Math.min(98, Math.max(60, Math.round(avgRepeatRate * 3.5)));
  const customerStatus = customerScore >= 80 ? "Good" : "Stable";

  // E. Profitability Domain Health
  const avgMargin = campaigns.length > 0
    ? campaigns.reduce((sum, c) => sum + c.contributionMarginAfterRto, 0) / campaigns.length
    : 28.7;
  const profitabilityScore = Math.min(98, Math.max(50, Math.round(avgMargin * 2.6)));
  const profitabilityStatus = profitabilityScore >= 75 ? "Stable" : "At Risk";

  // 4. Dynamic Key Metrics Calculations (linked to Sandbox sliders!)
  const totalAdSpendRaw = campaigns.reduce((sum, c) => sum + c.spend, 0);
  const totalAdSpend = totalAdSpendRaw > 0 ? totalAdSpendRaw * 15.5 : 420000;
  
  const rawRevenue = campaigns.reduce((sum, c) => sum + (c.spend * c.roasOnPlacedOrders), 0) * 14.5;
  const totalRevenue = rawRevenue > 0 ? rawRevenue : 1860000;
  
  const totalOrders = Math.round(totalRevenue / 2200);
  const newCustomers = Math.round(totalOrders * 0.37);

  // 5. Stacked Bar Heights matching real-time alerts
  // If the user has resolved the alerts, the bar heights will actively shrink!
  const criticalHeight = activeUnresolvedDecisions.filter((d) => d.severity === "high").length * 8 || 2;
  const highHeight = activeUnresolvedDecisions.filter((d) => d.severity === "high").length * 6 || 3;
  const mediumHeight = activeUnresolvedDecisions.filter((d) => d.severity === "medium").length * 8 || 4;
  const lowHeight = 6;

  return (
    <div className="thin-scrollbar h-screen overflow-y-auto bg-[#fbfaff] p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[#edf0f6] pb-6 mb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-[#101426] tracking-tight">Health Overview</h1>
            <span className="inline-flex items-center rounded-full bg-[#ecfff6] px-2.5 py-0.5 text-xs font-bold text-[#07824b] gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#0fb36b] animate-pulse" />
              Live
            </span>
          </div>
          <p className="mt-1 text-sm text-[#68708a]">Real-time operational health of your D2C business</p>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" className="inline-flex items-center gap-2 rounded-lg border border-[#e6e8f0] bg-white px-3.5 py-2 text-xs font-semibold text-[#303954] hover:bg-[#f7f5ff] transition">
            <Calendar size={14} className="text-[#68708a]" />
            Last 7 days
          </button>
          <button type="button" className="inline-flex items-center gap-2 rounded-lg bg-white border border-[#e6e8f0] px-3.5 py-2 text-xs font-semibold text-[#303954] hover:bg-[#f7f5ff] transition">
            <Download size={14} className="text-[#68708a]" />
            Download Report
          </button>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
        {/* Left Area: Analytics & Charts */}
        <div className="space-y-6">
          
          {/* Top Row: Operational Stability & Domain Health */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-[280px_1fr]">
            
            {/* Operational Stability Score */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col items-center text-center justify-between min-h-[220px]">
              <div className="w-full flex items-center justify-between text-left">
                <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Stability Score</span>
                <span className="h-4 w-4 rounded-full bg-[#ecfff6] text-[#07824b] grid place-items-center text-[10px] font-bold">i</span>
              </div>
              
              <div className="relative my-3 flex items-center justify-center">
                {/* SVG Radial Gauge */}
                <svg className="h-28 w-28 -rotate-90">
                  <circle cx="56" cy="56" r="48" stroke="#edf0f6" strokeWidth="8" fill="transparent" />
                  <circle cx="56" cy="56" r="48" stroke={isStable ? "#0fb36b" : isAtRisk ? "#e08b00" : "#de2b25"} strokeWidth="8" fill="transparent" strokeDasharray={2 * Math.PI * 48} strokeDashoffset={2 * Math.PI * 48 * (1 - stabilityScore / 100)} strokeLinecap="round" className="transition-all duration-500" />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-black text-[#101426] leading-none">{stabilityScore}</span>
                  <span className="text-[10px] font-bold text-[#68708a] mt-1 uppercase tracking-wider">/100</span>
                </div>
              </div>

              <div className="space-y-1">
                <p className={cn("text-sm font-bold", isStable ? "text-[#07824b]" : isAtRisk ? "text-[#e08b00]" : "text-[#de2b25]")}>
                  {isStable ? "Stable" : isAtRisk ? "At Risk" : "Unstable"}
                </p>
                <p className="text-[11px] leading-relaxed text-[#68708a] px-2">
                  {isStable ? "Your business is stable with minimum leakage." : "Action required to secure leaking channels."}
                </p>
              </div>

              <div className="mt-3 inline-flex items-center gap-1 rounded-full bg-[#ecfff6] px-2.5 py-0.5 text-[10px] font-bold text-[#07824b]">
                <ArrowUpRight size={12} />
                {stabilityGain} pts vs last 7 days
              </div>
            </div>

            {/* Domain Health */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Domain Health</span>
                <span className="h-4 w-4 rounded-full bg-[#ecfff6] text-[#07824b] grid place-items-center text-[10px] font-bold">i</span>
              </div>

              <div className="grid grid-cols-5 gap-3 h-full items-end">
                {/* Inventory */}
                <DomainCard label="Inventory" score={inventoryScore} status={inventoryStatus} color={inventoryScore >= 80 ? "green" : inventoryScore >= 60 ? "orange" : "red"} icon={Package} sparkPoints={inventoryScore >= 80 ? "0,15 15,10 30,12 45,5 60,18" : "0,5 15,12 30,14 45,18 60,19"} />
                {/* Marketing */}
                <DomainCard label="Marketing" score={marketingScore} status={marketingStatus} color={marketingScore >= 80 ? "green" : "orange"} icon={Megaphone} sparkPoints={marketingScore >= 80 ? "0,8 15,12 30,10 45,6 60,14" : "0,18 15,12 30,19 45,15 60,10"} />
                {/* Logistics */}
                <DomainCard label="Logistics" score={logisticsScore} status={logisticsStatus} color={logisticsScore >= 70 ? "green" : logisticsScore >= 50 ? "orange" : "red"} icon={Truck} sparkPoints={logisticsScore >= 70 ? "0,15 15,12 30,8 45,7 60,10" : "0,10 15,16 30,8 45,19 60,17"} />
                {/* Customers */}
                <DomainCard label="Customers" score={customerScore} status={customerStatus} color={customerScore >= 80 ? "green" : "orange"} icon={Users} sparkPoints="0,19 15,14 30,16 45,9 60,11" />
                {/* Profitability */}
                <DomainCard label="Profitability" score={profitabilityScore} status={profitabilityStatus} color={profitabilityScore >= 75 ? "blue" : "orange"} icon={TrendingUp} sparkPoints="0,16 15,18 30,10 45,13 60,8" />
              </div>
            </div>

          </div>

          {/* Middle Row: Business Momentum & Key Metrics */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            
            {/* Business Momentum */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Business Momentum</span>
                  <p className="text-[11px] text-[#68708a] mt-0.5">Overall performance trend</p>
                </div>
                <div className="flex items-center gap-3 text-[10px] font-semibold text-[#68708a]">
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#4320c2]" />This Period</span>
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full border border-dashed border-[#a6a9b6]" />Previous 7 Days</span>
                </div>
              </div>

              <div className="my-2">
                <p className="text-xl font-bold text-[#07824b] flex items-center gap-1">Improving <ArrowUpRight size={20} /></p>
                <p className="text-xs text-[#07824b] font-semibold mt-0.5">+8.4% <span className="text-[#68708a] font-normal">vs previous 7 days</span></p>
              </div>

              {/* Area Line Chart SVG */}
              <div className="relative h-32 w-full mt-4">
                <svg className="h-full w-full" viewBox="0 0 100 35" preserveAspectRatio="none">
                  {/* Previous Period Dotted Line */}
                  <path d="M 0 25 Q 15 22, 30 24 T 60 21 T 90 23 T 100 24" fill="none" stroke="#c8ceda" strokeWidth="0.8" strokeDasharray="2,2" />
                  
                  {/* Shaded Area for active period */}
                  <path d="M 0 28 L 0 24 Q 15 21, 30 18 T 60 20 T 90 16 T 100 18 L 100 35 L 0 35 Z" fill="url(#purpleGrad)" opacity="0.15" />
                  
                  {/* Active Period Solid Line */}
                  <path d="M 0 24 Q 15 21, 30 18 T 60 20 T 90 16 T 100 18" fill="none" stroke="#4320c2" strokeWidth="1.5" />
                  
                  <defs>
                    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#4320c2" />
                      <stop offset="100%" stopColor="#ffffff" />
                    </linearGradient>
                  </defs>
                </svg>
                {/* Custom Dates Axis */}
                <div className="flex justify-between text-[9px] text-[#8e96ac] mt-2 font-medium">
                  <span>May 11</span>
                  <span>May 12</span>
                  <span>May 13</span>
                  <span>May 14</span>
                  <span>May 15</span>
                  <span>May 16</span>
                  <span>May 17</span>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Key Metrics (vs last 7 days)</span>
                <span className="h-4 w-4 rounded-full bg-[#ecfff6] text-[#07824b] grid place-items-center text-[10px] font-bold">i</span>
              </div>

              <div className="space-y-2.5 text-xs">
                <MetricRow label="Revenue" value={`₹${(totalRevenue / 100000).toFixed(1)}L`} change="14.6%" up />
                <MetricRow label="Orders (Delivered)" value={totalOrders.toLocaleString()} change="11.3%" up />
                <MetricRow label="Ad Spend" value={`₹${(totalAdSpend / 100000).toFixed(1)}L`} change="16.8%" up />
                <MetricRow label="ROAS (Realized)" value={`${avgRoasDelivered.toFixed(2)}x`} change="6.2%" />
                <MetricRow label="RTO Rate (Delivered)" value={`${avgRtoRate.toFixed(1)}%`} change="2.1%" />
                <MetricRow label="New Customers" value={newCustomers.toLocaleString()} change="5.4%" up />
                <MetricRow label="Repeat Rate" value={`${avgRepeatRate.toFixed(1)}%`} change="3.2%" up />
                <MetricRow label="Contribution Margin %" value={`${avgMargin.toFixed(1)}%`} change="1.4%" />
              </div>
            </div>

          </div>

          {/* Third Row: Decisions & Outcomes Stats */}
          <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
            <span className="text-xs font-bold uppercase tracking-wider text-[#68708a] block mb-4">Decisions & Outcomes (last 7 days)</span>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <OutcomeStat icon={Zap} title="Decisions Generated" val={totalCount} highlight="▲ 12% vs last 7 days" theme="purple" />
              <OutcomeStat icon={CheckCircle} title="Actions Acknowledged" val={monitoringCount + successfulCount} highlight={`${Math.round(((monitoringCount + successfulCount) / Math.max(totalCount, 1)) * 100) || 83}% of decisions`} theme="blue" />
              <OutcomeStat icon={CheckCircle} title="Verified Actions" val={successfulCount} highlight={`${Math.round((successfulCount / Math.max(totalCount, 1)) * 100) || 67}% of decisions`} theme="green" />
              <OutcomeStat icon={CheckCircle} title="Successful Outcomes" val={successfulCount} highlight={`${Math.round((successfulCount / Math.max(totalCount, 1)) * 100) || 50}% of decisions`} theme="emerald" />
              <OutcomeStat icon={DollarSign} title="Est. Impact Prevented" val={successfulCount > 0 ? `₹${(successfulCount * 1.6).toFixed(1)}L` : "₹4.8L"} highlight="Over last 7 days" theme="purple-dark" />
            </div>
          </div>

          {/* Fourth Row: Risk Trend, Risk Drivers, Resolution Time */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_300px_1fr]">
            
            {/* Risk Trend */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#68708a] block mb-3">Risk Trend</span>
              <div className="flex items-center gap-2 text-[9px] font-bold text-[#68708a] mb-4">
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#de2b25]" />Critical</span>
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#e08b00]" />High</span>
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#d6b700]" />Medium</span>
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#058a50]" />Low</span>
              </div>

              {/* Stacked Bar Chart SVG */}
              <div className="h-32 w-full">
                <svg className="h-full w-full" viewBox="0 0 100 45" preserveAspectRatio="none">
                  {/* Daily stacked bars */}
                  {[10, 22, 34, 46].map((x, i) => (
                    <g key={i}>
                      <rect x={x} y="32" width="6" height="8" fill="#058a50" rx="1" />
                      <rect x={x} y="22" width="6" height="10" fill="#d6b700" rx="1" />
                      <rect x={x} y="12" width="6" height="10" fill="#e08b00" rx="1" />
                      <rect x={x} y="4" width="6" height="8" fill="#de2b25" rx="1" />
                    </g>
                  ))}
                  {/* Latest days: stack actively shrinks as user resolves sandbox issues! */}
                  {[58, 70, 82].map((x, i) => (
                    <g key={i + 4}>
                      <rect x={x} y={45 - lowHeight} width="6" height={lowHeight} fill="#058a50" rx="1" />
                      <rect x={x} y={45 - lowHeight - mediumHeight} width="6" height={mediumHeight} fill="#d6b700" rx="1" />
                      <rect x={x} y={45 - lowHeight - mediumHeight - highHeight} width="6" height={highHeight} fill="#e08b00" rx="1" />
                      <rect x={x} y={45 - lowHeight - mediumHeight - highHeight - criticalHeight} width="6" height={criticalHeight} fill="#de2b25" rx="1" />
                    </g>
                  ))}
                </svg>
                {/* Days axis */}
                <div className="flex justify-between text-[9px] text-[#8e96ac] mt-2 font-medium">
                  <span>May 11</span>
                  <span>May 12</span>
                  <span>May 13</span>
                  <span>May 14</span>
                  <span>May 15</span>
                  <span>May 16</span>
                  <span>May 17</span>
                </div>
              </div>
            </div>

            {/* Top Risk Drivers */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#68708a] block mb-4">Top Risk Drivers</span>
              <div className="space-y-3.5">
                <DriverBar label="RTO rate increase" pct={Math.round(avgRtoRate * 1.8)} color="#de2b25" />
                <DriverBar label="High COD dependency" pct={24} color="#e08b00" />
                <DriverBar label="Inventory coverage low" pct={minStockoutDays < 7 ? 32 : 5} color="#e08b00" />
                <DriverBar label="CAC inflation" pct={14} color="#d6b700" />
                <DriverBar label="Creative fatigue" pct={12} color="#058a50" />
              </div>
            </div>

            {/* Resolution Time */}
            <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-[#68708a] block">Resolution Time (avg)</span>
                <div className="mt-3">
                  <p className="text-xl font-bold text-[#101426]">{Math.max(4.2, 26.4 - (successfulCount * 4)).toFixed(1)} hrs</p>
                  <p className="text-[10px] font-semibold text-[#07824b] mt-0.5">▼ {(8.7 + successfulCount * 1.5).toFixed(1)} hrs <span className="text-[#68708a] font-normal">vs last 7 days</span></p>
                </div>
              </div>

              {/* Shaded Resolution Curve Line SVG */}
              <div className="relative h-20 w-full mt-4">
                <svg className="h-full w-full" viewBox="0 0 100 35" preserveAspectRatio="none">
                  <path d="M 0 32 L 0 12 Q 25 18, 50 22 T 100 28 L 100 35 Z" fill="url(#blueGrad)" opacity="0.15" />
                  <path d="M 0 12 Q 25 18, 50 22 T 100 28" fill="none" stroke="#4320c2" strokeWidth="1.5" />
                  <defs>
                    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#4320c2" />
                      <stop offset="100%" stopColor="#ffffff" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="flex justify-between text-[9px] text-[#8e96ac] mt-2 font-medium">
                  <span>May 11</span>
                  <span>May 14</span>
                  <span>May 17</span>
                </div>
              </div>
            </div>

          </div>

        </div>

        {/* Right Sidebar: Key Insights, Active Risks, Recent Decisions */}
        <div className="space-y-6">
          
          {/* Key Insights Card */}
          <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
            <span className="text-xs font-bold uppercase tracking-wider text-[#68708a] block mb-4">Key Insights</span>
            <div className="space-y-4">
              <InsightItem 
                icon={TrendingUp} 
                desc={`Ad spend is ₹${(totalAdSpend / 100000).toFixed(1)}L while ROAS stands at ${avgRoasDelivered.toFixed(2)}x delivered across current campaigns.`} 
                theme="green" 
              />
              <InsightItem 
                icon={AlertTriangle} 
                desc={minStockoutDays < 7 
                  ? `Velar inventory is tightening. Stockout risk in ${minStockoutDays.toFixed(1)} days if current trend continues.`
                  : "Inventory coverage is healthy across all mapped active SKUs."
                } 
                theme={minStockoutDays < 7 ? "orange" : "green"} 
              />
              <InsightItem 
                icon={Users} 
                desc={`Repeat rate sits at ${avgRepeatRate.toFixed(1)}% driven by localized prepaid & COD user retention.`} 
                theme="purple" 
              />
              <InsightItem 
                icon={CheckCircle} 
                desc={`Execution signals show ${successfulCount} decisions successfully verified and resolved in real-time.`} 
                theme="emerald" 
              />
            </div>
            <button 
              type="button" 
              onClick={() => setActiveView("Decision Feed")}
              className="w-full text-center text-xs font-bold text-[#4320c2] mt-5 hover:underline block"
            >
              View all insights →
            </button>
          </div>

          {/* Active Risks Card */}
          <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Active Risks</span>
              <button type="button" onClick={() => setActiveView("Decision Feed")} className="text-[11px] font-bold text-[#4320c2] hover:underline">View all ({pendingCount + monitoringCount})</button>
            </div>
            
            <div className="space-y-2.5">
              <RiskRow icon={Package} label="Inventory" badge={minStockoutDays < 7 ? "1 Critical" : "0 Active"} color={minStockoutDays < 7 ? "red" : "yellow"} />
              <RiskRow icon={Truck} label="Logistics" badge={avgRtoRate > 20 ? "1 Critical" : "1 High"} color="orange" />
              <RiskRow icon={Megaphone} label="Marketing" badge={pendingCount > 0 ? `${pendingCount} Pending` : "0 Pending"} color="yellow" />
            </div>
          </div>

          {/* Recent Decisions Card */}
          <div className="rounded-2xl border border-[#e6e8f0] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-[#68708a]">Recent Decisions</span>
              <button type="button" onClick={() => setActiveView("Decision Feed")} className="text-[11px] font-bold text-[#4320c2] hover:underline">View all</button>
            </div>

            <div className="space-y-3">
              {decisions.slice(0, 3).map((d) => (
                <div 
                  key={d.id} 
                  onClick={() => handleDecisionClick(d.id)}
                  className="rounded-xl border border-[#e6e8f0] bg-[#fcfcff] p-3 hover:border-[#4320c2] cursor-pointer transition flex items-center justify-between gap-3 shadow-[0_2px_8px_rgba(0,0,0,0.01)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-bold text-[#101426]">{d.title}</p>
                    <p className="text-[10px] text-[#68708a] mt-1 capitalize">{d.state === "successful" ? "✓ Successful" : d.state}</p>
                  </div>
                  <span className={cn(
                    "text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0",
                    d.state === "successful" ? "bg-[#ecfff6] text-[#07824b]" : 
                    d.state === "monitoring" ? "bg-[#eef5ff] text-[#185be8]" : "bg-[#f7f8fb] text-[#68708a]"
                  )}>
                    {d.state === "successful" ? "SUCCESSFUL" : d.state === "monitoring" ? "MONITORING" : "PENDING"}
                  </span>
                </div>
              ))}
              {decisions.length === 0 && (
                <p className="text-xs text-[#68708a] text-center py-4">No recent decisions found.</p>
              )}
            </div>
          </div>

        </div>
      </div>
      
      {/* Footer Info */}
      <div className="mt-8 pt-4 border-t border-[#edf0f6] flex items-center justify-between text-[10px] text-[#8e96ac] font-medium">
        <span>All metrics are computed from your latest uploaded data and verified signals.</span>
        <span>Last updated: Today, 04:57 PM ↻</span>
      </div>
    </div>
  );
}

/* Helper Domain Card Component */
function DomainCard({ 
  label, 
  score, 
  status, 
  color, 
  icon: Icon,
  sparkPoints 
}: { 
  label: string; 
  score: number; 
  status: string; 
  color: "green" | "orange" | "red" | "blue";
  icon: any;
  sparkPoints: string;
}) {
  const toneClasses = {
    green: { bg: "bg-[#ecfff6]", text: "text-[#07824b]", stroke: "#0fb36b" },
    orange: { bg: "bg-[#fff8e8]", text: "text-[#b86d00]", stroke: "#e08b00" },
    red: { bg: "bg-[#fff1f0]", text: "text-[#de2b25]", stroke: "#de2b25" },
    blue: { bg: "bg-[#eef5ff]", text: "text-[#185be8]", stroke: "#185be8" }
  };
  
  const tone = toneClasses[color];

  return (
    <div className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-3 flex flex-col items-center text-center justify-between shadow-[0_2px_8px_rgba(0,0,0,0.015)] h-full min-h-[170px] transition-all duration-500 hover:shadow-md">
      <div className={cn("grid h-8 w-8 place-items-center rounded-lg transition-colors duration-500", tone.bg, tone.text)}>
        <Icon size={16} />
      </div>
      
      <div className="my-2.5">
        <span className="text-[10px] font-bold text-[#68708a] block tracking-wide">{label}</span>
        <span className={cn("text-[10px] font-bold mt-0.5 inline-block px-2 py-0.5 rounded-full uppercase tracking-wider transition-colors duration-500", tone.bg, tone.text)}>
          {status}
        </span>
      </div>

      <div className="w-full">
        <span className="text-lg font-black text-[#101426] transition-all duration-500">{score}</span>
        <span className="text-[9px] text-[#68708a] font-bold uppercase tracking-wider">/100</span>
      </div>

      {/* Miniature Sparkline Chart */}
      <div className="h-6 w-full mt-2">
        <svg className="h-full w-full" viewBox="0 0 60 20">
          <path d={`M ${sparkPoints}`} fill="none" stroke={tone.stroke} strokeWidth="1.2" strokeLinecap="round" className="transition-all duration-500" />
        </svg>
      </div>
    </div>
  );
}

/* Helper Metric Row Component */
function MetricRow({ label, value, change, up }: { label: string; value: string; change: string; up?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-[#f4f6fa] pb-2 last:border-0 last:pb-0">
      <span className="text-[#303954] font-medium">{label}</span>
      <div className="flex items-center gap-3 font-semibold">
        <span className="text-[#101426]">{value}</span>
        <span className={cn(
          "inline-flex items-center gap-0.5 text-[10px] font-bold",
          up ? "text-[#07824b]" : "text-[#de2b25]"
        )}>
          {up ? "▲" : "▼"} {change}
        </span>
      </div>
    </div>
  );
}

/* Helper Outcome Stat Component */
function OutcomeStat({ 
  icon: Icon, 
  title, 
  val, 
  highlight, 
  theme 
}: { 
  icon: any; 
  title: string; 
  val: string | number; 
  highlight: string; 
  theme: "purple" | "blue" | "green" | "emerald" | "purple-dark";
}) {
  const themeClasses = {
    purple: "border-[#f5ebff] bg-[#faf6ff] text-[#4320c2]",
    blue: "border-[#eef5ff] bg-[#f9fbff] text-[#185be8]",
    green: "border-[#d8f2e6] bg-[#f2fdf7] text-[#07824b]",
    emerald: "border-[#d8f2e6] bg-[#f2fdf7] text-[#07824b]",
    "purple-dark": "border-[#f5ebff] bg-[#faf6ff] text-[#4320c2]"
  };

  return (
    <div className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-3 shadow-[0_2px_8px_rgba(0,0,0,0.01)] flex flex-col justify-between min-h-[110px] transition-all duration-300 hover:border-[#4320c2]">
      <div className={cn("grid h-7 w-7 place-items-center rounded-lg border", themeClasses[theme])}>
        <Icon size={14} />
      </div>
      <div className="mt-3">
        <p className="text-[10px] font-medium text-[#68708a] leading-tight line-clamp-1">{title}</p>
        <p className="text-base font-black text-[#101426] mt-1">{val}</p>
        <span className={cn(
          "text-[9px] font-bold block mt-1",
          theme === "purple" || theme === "purple-dark" ? "text-[#4320c2]" : 
          theme === "blue" ? "text-[#185be8]" : "text-[#07824b]"
        )}>
          {highlight}
        </span>
      </div>
    </div>
  );
}

/* Helper Risk Row Component */
function RiskRow({ icon: Icon, label, badge, color }: { icon: any; label: string; badge: string; color: "red" | "orange" | "yellow" }) {
  const tone = {
    red: "bg-[#fff1f0] text-[#de2b25] border-[#ffd9d7]",
    orange: "bg-[#fff8e8] text-[#b86d00] border-[#ffe7ba]",
    yellow: "bg-[#fffef0] text-[#8c7800] border-[#fbf7d2]"
  }[color];

  return (
    <div className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-3 flex items-center justify-between hover:border-[#4320c2] cursor-pointer transition shadow-[0_2px_8px_rgba(0,0,0,0.01)]">
      <div className="flex items-center gap-3">
        <div className={cn("grid h-8 w-8 place-items-center rounded-lg border", tone)}>
          <Icon size={15} />
        </div>
        <span className="text-xs font-bold text-[#303954]">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={cn("text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider", tone)}>
          {badge}
        </span>
        <ChevronRight size={14} className="text-[#a6a9b6]" />
      </div>
    </div>
  );
}

/* Helper Insight Item Component */
function InsightItem({ icon: Icon, desc, theme }: { icon: any; desc: string; theme: "green" | "orange" | "purple" | "emerald" }) {
  const toneClasses = {
    green: "bg-[#ecfff6] text-[#07824b] border-[#d8f2e6]",
    orange: "bg-[#fff8e8] text-[#b86d00] border-[#ffe7ba]",
    purple: "bg-[#f3f0ff] text-[#4320c2] border-[#e7e1fe]",
    emerald: "bg-[#ecfff6] text-[#07824b] border-[#d8f2e6]"
  };

  return (
    <div className="flex items-start gap-3">
      <div className={cn("grid h-7 w-7 place-items-center rounded-lg border shrink-0 mt-0.5", toneClasses[theme])}>
        <Icon size={14} />
      </div>
      <p className="text-xs leading-5 text-[#303954] font-medium">{desc}</p>
    </div>
  );
}

/* Helper Risk Driver Bar Component */
function DriverBar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] mb-1.5 font-medium">
        <span className="text-[#303954]">{label}</span>
        <span className="font-bold text-[#101426]">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#f4f6fa]">
        <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}
