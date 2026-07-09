import React from "react";
import { Check } from "lucide-react";

export default function PlanCard({ plan, current, popular, onSelect, ctaLabel, disabled, dark = true }) {
  return (
    <div
      data-testid={`plan-card-${plan.id}`}
      className={`relative rounded-2xl border p-8 flex flex-col transition-colors ${
        current
          ? "border-emerald-500 bg-emerald-500/[0.06]"
          : dark
          ? "border-white/10 bg-[#121826] hover:border-white/25"
          : "border-black/10 bg-white hover:border-black/25"
      }`}
    >
      {popular && (
        <span className="absolute -top-3 left-8 rounded-full bg-emerald-500 text-[#0b0f19] text-xs font-bold px-3 py-1">
          Most popular
        </span>
      )}
      {current && (
        <span className="absolute -top-3 right-8 rounded-full bg-white/10 text-emerald-400 border border-emerald-500/40 text-xs font-semibold px-3 py-1">
          Current plan
        </span>
      )}
      <h3 className={`font-dash-head text-xl font-bold ${dark ? "text-white" : "text-[#111827]"}`}>{plan.name}</h3>
      <p className={`text-sm mt-1 ${dark ? "text-slate-400" : "text-[#6B7280]"} min-h-[40px]`}>{plan.tagline}</p>
      <div className="mt-4 flex items-baseline gap-1">
        <span className={`font-dash-head text-4xl font-bold ${dark ? "text-white" : "text-[#111827]"}`}>${plan.price}</span>
        <span className={`text-sm ${dark ? "text-slate-500" : "text-[#6B7280]"}`}>/month</span>
      </div>
      <ul className="mt-6 space-y-3 flex-1">
        {plan.features.map((f) => (
          <li key={f} className={`flex items-start gap-2 text-sm ${dark ? "text-slate-300" : "text-[#374151]"}`}>
            <Check className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
            {f}
          </li>
        ))}
      </ul>
      {onSelect && (
        <button
          onClick={() => onSelect(plan)}
          disabled={disabled || current}
          data-testid={`select-plan-${plan.id}`}
          className={`mt-8 rounded-full px-6 py-3 text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            popular
              ? "bg-emerald-500 text-[#0b0f19] hover:bg-emerald-400"
              : dark
              ? "border border-white/20 text-white hover:bg-white/5"
              : "border border-black/15 text-[#111827] hover:bg-black/[0.03]"
          }`}
        >
          {current ? "Current plan" : ctaLabel || "Choose plan"}
        </button>
      )}
    </div>
  );
}
