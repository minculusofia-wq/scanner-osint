"use client";

import type { EscalationTracker } from "@/types/intelligence";
import { EscalationLevelBadge } from "./EscalationLevelBadge";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}j`;
}

export function EscalationCard({
  tracker,
}: {
  tracker: EscalationTracker;
}) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">
            {tracker.name}
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">
            {tracker.region.replace("_", " ")} &middot;{" "}
            {tracker.category || "general"}
          </p>
        </div>
        <EscalationLevelBadge
          level={tracker.escalation_level}
          score={tracker.escalation_score}
        />
      </div>

      {/* Signal stats */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-800/50 rounded-lg px-3 py-2 text-center">
          <div className="text-lg font-bold text-white">
            {tracker.signal_count_1h}
          </div>
          <div className="text-[10px] text-gray-500 uppercase">1h</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg px-3 py-2 text-center">
          <div className="text-lg font-bold text-white">
            {tracker.signal_count_6h}
          </div>
          <div className="text-[10px] text-gray-500 uppercase">6h</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg px-3 py-2 text-center">
          <div className="text-lg font-bold text-white">
            {tracker.signal_count_24h}
          </div>
          <div className="text-[10px] text-gray-500 uppercase">24h</div>
        </div>
      </div>

      {/* Sources */}
      {tracker.unique_sources_1h > 0 && (
        <div className="text-xs text-gray-400">
          <span className="font-medium text-gray-300">
            {tracker.unique_sources_1h}
          </span>{" "}
          sources (1h) &middot;{" "}
          {(tracker.contributing_source_types ?? []).slice(0, 5).join(", ")}
        </div>
      )}

      {/* Patterns */}
      {(tracker.matched_patterns ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tracker.matched_patterns.slice(0, 3).map((p) => (
            <span
              key={p}
              className="px-2 py-0.5 text-[10px] rounded-full bg-red-500/10 text-red-400 border border-red-500/20"
            >
              {p.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Key Headlines */}
      {tracker.key_headlines && tracker.key_headlines.length > 0 && (
        <div className="space-y-1.5 border-t border-gray-800 pt-2">
          <div className="text-[10px] uppercase text-gray-500 font-medium tracking-wider">
            Signaux clés
          </div>
          {tracker.key_headlines.slice(0, 3).map((h, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                {(h.source || "?").replace(/_/g, " ").slice(0, 12)}
              </span>
              <span className="text-gray-300 line-clamp-1">{h.title}</span>
            </div>
          ))}
        </div>
      )}

      {/* Countries */}
      {tracker.countries.length > 0 && (
        <div className="text-xs text-gray-500">
          {tracker.countries.slice(0, 5).join(", ")}
        </div>
      )}

      {/* Markets */}
      {tracker.linked_markets.length > 0 && (
        <div className="border-t border-gray-800 pt-2 space-y-1">
          {tracker.linked_markets.slice(0, 2).map((m, i) => (
            <div key={i} className="text-xs text-indigo-400 truncate">
              {m.question}
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] text-gray-600">
        <span>
          {tracker.previous_level !== tracker.escalation_level &&
            `${tracker.previous_level} -> `}
          {tracker.level_changed_at && `il y a ${timeAgo(tracker.level_changed_at)}`}
        </span>
        <span>MAJ {timeAgo(tracker.updated_at)}</span>
      </div>
    </div>
  );
}
