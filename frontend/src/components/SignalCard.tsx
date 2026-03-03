"use client";

import type { IntelligenceBrief } from "@/types/intelligence";
import { PriorityBadge } from "./PriorityBadge";

export function SignalCard({ brief }: { brief: IntelligenceBrief }) {
  const marketCount = brief.linked_markets.length;
  const topMarket = brief.linked_markets[0];

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-3 hover:border-indigo-500/50 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <PriorityBadge urgency={brief.urgency} />
        <span className="text-xs text-gray-500 truncate">{brief.category}</span>
      </div>

      <h4 className="text-sm font-medium text-white mb-1 line-clamp-2">
        {brief.title}
      </h4>

      {brief.trading_implication && (
        <p className="text-xs text-gray-400 mb-2 line-clamp-2">
          {brief.trading_implication}
        </p>
      )}

      {topMarket && (
        <a
          href={`https://polymarket.com/event/${topMarket.condition_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-xs text-indigo-400 hover:text-indigo-300 truncate"
        >
          → {topMarket.question}
        </a>
      )}

      <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
        <span>{brief.source_count} src{brief.source_count > 1 ? "s" : ""}</span>
        {marketCount > 1 && <span>+{marketCount - 1} marchés</span>}
        <span>{Math.round(brief.confidence * 100)}%</span>
      </div>
    </div>
  );
}
