import type { IntelligenceStats } from "@/types/intelligence";
import { timeAgo } from "@/lib/utils";

const stats_items = [
  { key: "items_last_24h", label: "Éléments (24h)" },
  { key: "briefs_count", label: "Résumés actifs" },
  { key: "actionable_briefs", label: "Actionnables" },
  { key: "linked_markets_count", label: "Marchés liés" },
] as const;

export function StatsBar({ stats }: { stats: IntelligenceStats | null }) {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {stats_items.map(({ key, label }) => (
        <div
          key={key}
          className="rounded-lg bg-gray-900 border border-gray-800 px-4 py-3"
        >
          <div className="text-2xl font-bold text-white">
            {stats[key]}
          </div>
          <div className="text-xs text-gray-400">{label}</div>
        </div>
      ))}
      <div className="rounded-lg bg-gray-900 border border-gray-800 px-4 py-3">
        <div className="text-sm font-medium text-white">
          {stats.sources_active.length > 0
            ? stats.sources_active.join(", ").toUpperCase()
            : "Aucune"}
        </div>
        <div className="text-xs text-gray-400">
          Sources actives
          {stats.last_collection_at && (
            <span className="ml-1">
              ({timeAgo(stats.last_collection_at)})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
