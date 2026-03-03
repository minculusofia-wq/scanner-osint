"use client";

import type { IntelligenceItem } from "@/types/intelligence";
import { PriorityBadge } from "./PriorityBadge";
import { SourceBadge } from "./SourceBadge";
import { SentimentIndicator } from "./SentimentIndicator";
import { timeAgo } from "@/lib/utils";

export function ItemCard({ item }: { item: IntelligenceItem }) {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-3 hover:border-gray-700 transition-colors">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {/* Header badges */}
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <SourceBadge source={item.source} />
            <PriorityBadge urgency={item.urgency} />
            {item.category !== "general" && (
              <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                {item.category}
              </span>
            )}
            {item.region && (
              <span className="text-xs text-gray-600">{item.region}</span>
            )}
          </div>

          {/* Title */}
          {item.url ? (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-white hover:text-indigo-400 transition-colors font-medium leading-tight line-clamp-2"
            >
              {item.title}
            </a>
          ) : (
            <p className="text-sm text-white font-medium leading-tight line-clamp-2">
              {item.title}
            </p>
          )}

          {/* Summary */}
          {item.summary && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">
              {item.summary}
            </p>
          )}

          {/* Footer */}
          <div className="flex items-center gap-3 mt-2">
            <SentimentIndicator score={item.sentiment_score} />
            <span className="text-xs text-gray-600">
              Score: {item.priority_score.toFixed(0)}
            </span>
            {item.linked_markets.length > 0 && (
              <span className="text-xs text-indigo-400">
                {item.linked_markets.length} marché{item.linked_markets.length > 1 ? "s" : ""}
              </span>
            )}
            <span className="text-xs text-gray-600 ml-auto">
              {timeAgo(item.published_at || item.collected_at)}
            </span>
          </div>
        </div>

        {/* Thumbnail */}
        {item.image_url && (
          <img
            src={item.image_url}
            alt=""
            className="w-16 h-16 rounded object-cover shrink-0 bg-gray-800"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        )}
      </div>
    </div>
  );
}
