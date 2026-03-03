"use client";

import type { IntelligenceBrief } from "@/types/intelligence";
import { PriorityBadge } from "./PriorityBadge";
import { MarketLink } from "./MarketLink";
import { timeAgo } from "@/lib/utils";

interface BriefCardProps {
  brief: IntelligenceBrief;
  onDismiss?: (id: number) => void;
}

export function BriefCard({ brief, onDismiss }: BriefCardProps) {
  const confidencePct = Math.round(brief.confidence * 100);

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4 space-y-3 hover:border-gray-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <PriorityBadge urgency={brief.urgency} />
            <span className="text-xs text-gray-500">{brief.category}</span>
            {brief.region && (
              <span className="text-xs text-gray-500">{brief.region}</span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-white leading-tight">
            {brief.title}
          </h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-500">
            {brief.source_count} source{brief.source_count > 1 ? "s" : ""}
          </span>
          {onDismiss && (
            <button
              onClick={() => onDismiss(brief.id)}
              className="text-gray-500 hover:text-gray-300 text-xs"
              title="Ignorer"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">
        {brief.summary}
      </p>

      {/* Trading Implication */}
      {brief.trading_implication && (
        <div className="rounded bg-gray-800/60 border border-gray-700/50 px-3 py-2">
          <div className="text-xs text-gray-500 mb-0.5">Signal trading</div>
          <p className="text-xs text-gray-300">{brief.trading_implication}</p>
        </div>
      )}

      {/* Confidence bar */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Confiance</span>
        <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${confidencePct}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{confidencePct}%</span>
      </div>

      {/* Linked Markets */}
      {brief.linked_markets.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {brief.linked_markets.map((m, i) => (
            <MarketLink key={i} market={m} />
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Priorité : {brief.priority_score.toFixed(0)}</span>
        <span>{timeAgo(brief.created_at)}</span>
      </div>
    </div>
  );
}
