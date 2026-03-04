import { cn } from "@/lib/utils";

const SOURCE_STYLES: Record<string, string> = {
  // News/Data
  gdelt: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  newsdata: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  acled: "bg-red-500/20 text-red-400 border-red-500/30",
  finnhub: "bg-green-500/20 text-green-400 border-green-500/30",
  reddit: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  // FININT
  sec_edgar: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  whale_crypto: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  fred: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  // GEOINT
  adsb: "bg-sky-500/20 text-sky-400 border-sky-500/30",
  nasa_firms: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  ship_tracker: "bg-teal-500/20 text-teal-400 border-teal-500/30",
  usgs_earthquake: "bg-rose-500/20 text-rose-400 border-rose-500/30",
  noaa_weather: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  // Behavioral OSINT
  pentagon_pizza: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  // Conflict OSINT
  liveuamap: "bg-red-600/20 text-red-400 border-red-600/30",
  nuclear_monitor: "bg-yellow-600/20 text-yellow-400 border-yellow-600/30",
  // Social OSINT
  telegram: "bg-blue-400/20 text-blue-300 border-blue-400/30",
  gov_rss: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

export function SourceBadge({ source }: { source: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
        SOURCE_STYLES[source] || "bg-gray-500/20 text-gray-400 border-gray-500/30"
      )}
    >
      {source.replace(/_/g, " ").toUpperCase()}
    </span>
  );
}
