"use client";

interface FiltersProps {
  filters: {
    category?: string;
    urgency?: string;
    source?: string;
  };
  onChange: (filters: {
    category?: string;
    urgency?: string;
    source?: string;
  }) => void;
}

const CATEGORIES = ["", "geopolitical", "financial", "conflict", "political", "crypto", "tech"];
const URGENCIES = ["", "critical", "high", "medium", "low"];
const SOURCES = [
  "", "gdelt", "newsdata", "acled", "finnhub", "reddit",
  "sec_edgar", "whale_crypto", "fred",
  "adsb", "nasa_firms", "ship_tracker", "usgs_earthquake", "noaa_weather",
  "pentagon_pizza",
  "liveuamap", "nuclear_monitor",
  "telegram", "gov_rss",
];

function SelectFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (val: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-gray-400">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
      >
        <option value="">Tous</option>
        {options
          .filter((o) => o)
          .map((o) => (
            <option key={o} value={o}>
              {o.charAt(0).toUpperCase() + o.slice(1)}
            </option>
          ))}
      </select>
    </div>
  );
}

export function Filters({ filters, onChange }: FiltersProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <SelectFilter
        label="Catégorie"
        value={filters.category || ""}
        options={CATEGORIES}
        onChange={(v) => onChange({ ...filters, category: v || undefined })}
      />
      <SelectFilter
        label="Urgence"
        value={filters.urgency || ""}
        options={URGENCIES}
        onChange={(v) => onChange({ ...filters, urgency: v || undefined })}
      />
      <SelectFilter
        label="Source"
        value={filters.source || ""}
        options={SOURCES}
        onChange={(v) => onChange({ ...filters, source: v || undefined })}
      />
    </div>
  );
}
