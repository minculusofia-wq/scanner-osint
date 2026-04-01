"use client";

import { useMemo } from "react";
import { useIntelligence } from "@/hooks/useIntelligence";
import { Header } from "@/components/layout/Header";
import { PriorityBadge } from "@/components/PriorityBadge";
import { SentimentIndicator } from "@/components/SentimentIndicator";

interface MarketGroup {
  condition_id: string;
  question: string;
  slug: string;
  items: {
    id: number;
    title: string;
    source: string;
    urgency: string;
    sentiment_score: number;
    priority_score: number;
  }[];
  avg_sentiment: number;
  max_priority: number;
}

export default function MarketsPage() {
  const { items, loading, error } = useIntelligence(true);

  const marketGroups = useMemo(() => {
    const groups: Record<string, MarketGroup> = {};

    for (const item of items) {
      for (const market of item.linked_markets) {
        const key = market.condition_id;
        if (!groups[key]) {
          groups[key] = {
            condition_id: market.condition_id,
            question: market.question,
            slug: market.slug || "",
            items: [],
            avg_sentiment: 0,
            max_priority: 0,
          };
        }
        groups[key].items.push({
          id: item.id,
          title: item.title,
          source: item.source,
          urgency: item.urgency,
          sentiment_score: item.sentiment_score,
          priority_score: item.priority_score,
        });
      }
    }

    // Compute aggregates
    for (const group of Object.values(groups)) {
      const sentiments = group.items.map((i) => i.sentiment_score);
      group.avg_sentiment = sentiments.reduce((a, b) => a + b, 0) / sentiments.length;
      group.max_priority = Math.max(...group.items.map((i) => i.priority_score));
    }

    return Object.values(groups).sort((a, b) => b.max_priority - a.max_priority);
  }, [items]);

  return (
    <div className="space-y-6">
      <Header
        title="Marchés associés"
        subtitle={`${marketGroups.length} marchés Polymarket avec signaux de renseignement`}
      />

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && marketGroups.length === 0 ? (
        <div className="text-center py-16 text-gray-500">Chargement...</div>
      ) : marketGroups.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">📊</div>
          <p>Aucun marché associé. Lancez d'abord une collecte.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {marketGroups.map((group) => (
            <div
              key={group.condition_id}
              className="rounded-lg bg-gray-900 border border-gray-800 p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <a
                    href={group.slug ? `https://polymarket.com/event/${group.slug}` : `https://polymarket.com/markets?_q=${encodeURIComponent(group.question)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-white hover:text-indigo-400 transition-colors"
                  >
                    {group.question}
                  </a>
                  <div className="flex items-center gap-3 mt-1">
                    <SentimentIndicator score={group.avg_sentiment} />
                    <span className="text-xs text-gray-500">
                      {group.items.length} signal{group.items.length > 1 ? "aux" : ""}
                    </span>
                    <span className="text-xs text-gray-500">
                      Priorité max : {group.max_priority.toFixed(0)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                {group.items.slice(0, 5).map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <PriorityBadge urgency={item.urgency} />
                    <span className="text-gray-500 uppercase w-14">{item.source}</span>
                    <span className="text-gray-300 truncate">{item.title}</span>
                  </div>
                ))}
                {group.items.length > 5 && (
                  <p className="text-xs text-gray-600">
                    +{group.items.length - 5} autres signaux
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
