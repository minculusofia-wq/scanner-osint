import type { LinkedMarket } from "@/types/intelligence";

export function MarketLink({ market }: { market: LinkedMarket }) {
  return (
    <a
      href={market.slug ? `https://polymarket.com/event/${market.slug}` : `https://polymarket.com/markets?_q=${encodeURIComponent(market.question)}`}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 px-2 py-1 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs hover:bg-indigo-500/20 transition-colors"
    >
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
      </svg>
      <span className="truncate max-w-48">{market.question}</span>
    </a>
  );
}
