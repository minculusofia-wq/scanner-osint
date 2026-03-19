"use client";

import type { IntelligenceBrief } from "@/types/intelligence";
import { PriorityBadge } from "./PriorityBadge";
import { MarketLink } from "./MarketLink";
import { timeAgo } from "@/lib/utils";
import Link from "next/link";

interface BriefCardProps {
  brief: IntelligenceBrief;
  onDismiss?: (id: number) => void;
}

const CONVICTION_LABELS = ["", "Très faible", "Faible", "Modérée", "Forte", "Très forte"];
const CONVICTION_COLORS = [
  "",
  "bg-gray-500",
  "bg-yellow-500",
  "bg-orange-500",
  "bg-red-500",
  "bg-red-600",
];

export function BriefCard({ brief, onDismiss }: BriefCardProps) {
  const confidencePct = Math.round(brief.confidence * 100);
  const hasAI = !!brief.ai_situation;

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
            {hasAI && (
              <span className="px-1.5 py-0.5 text-[9px] rounded bg-violet-500/15 text-violet-400 border border-violet-500/20 font-medium">
                AI
              </span>
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

      {/* AI Analysis OR fallback to rule-based */}
      {hasAI ? (
        <div className="space-y-2">
          {/* Situation */}
          <div className="rounded bg-gray-800/80 px-3 py-2">
            <div className="text-[10px] uppercase text-gray-500 font-medium tracking-wider mb-1">
              Situation
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">
              {brief.ai_situation}
            </p>
          </div>

          {/* Analysis */}
          <div className="rounded bg-gray-800/60 px-3 py-2">
            <div className="text-[10px] uppercase text-gray-500 font-medium tracking-wider mb-1">
              Analyse
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">
              {brief.ai_analysis}
            </p>
          </div>

          {/* Trading Signal */}
          {brief.ai_trading_signal && (
            <div className="rounded border border-indigo-500/30 bg-indigo-500/5 px-3 py-2">
              <div className="flex items-center justify-between mb-1">
                <div className="text-[10px] uppercase text-indigo-400 font-medium tracking-wider">
                  Signal Trading
                </div>
                {brief.ai_confidence > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-gray-500">Conviction:</span>
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5].map((level) => (
                        <div
                          key={level}
                          className={`w-2 h-2 rounded-full ${
                            level <= brief.ai_confidence
                              ? CONVICTION_COLORS[brief.ai_confidence]
                              : "bg-gray-700"
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-[10px] text-gray-400">
                      {CONVICTION_LABELS[brief.ai_confidence] || ""}
                    </span>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-200 leading-relaxed">
                {brief.ai_trading_signal}
              </p>
            </div>
          )}

          {/* Risk Factors */}
          {brief.ai_risk_factors && (
            <div className="flex items-start gap-1.5 px-1">
              <span className="text-amber-500 text-xs mt-0.5 shrink-0">⚠</span>
              <p className="text-[11px] text-gray-500 leading-relaxed">
                {brief.ai_risk_factors}
              </p>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Fallback: rule-based summary + trading implication */}
          <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">
            {brief.summary}
          </p>
          {brief.trading_implication && (
            <div className="rounded bg-gray-800/60 border border-gray-700/50 px-3 py-2">
              <div className="text-xs text-gray-500 mb-0.5">Signal trading</div>
              <p className="text-xs text-gray-300">{brief.trading_implication}</p>
            </div>
          )}
        </>
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
      <div className="flex items-center justify-between pt-2 border-t border-gray-800/50">
        <div className="flex items-center gap-3 text-[11px] text-gray-500">
          <span>Priorité : {brief.priority_score.toFixed(0)}</span>
          <span>{timeAgo(brief.created_at)}</span>
        </div>
        <div className="flex items-center gap-3">
          <Link 
            href={`/chat?q=${encodeURIComponent("Peux-tu m'en dire plus sur : " + brief.title)}`}
            className="text-[11px] font-medium text-violet-400 hover:text-violet-300 flex items-center gap-1"
          >
            Analyser avec l'IA <span>💬</span>
          </Link>
          <Link 
            href={`/graph?briefId=${brief.id}`}
            className="text-[11px] font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            Visualiser le Graphe <span>→</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
