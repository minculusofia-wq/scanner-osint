import { cn } from "@/lib/utils";

const URGENCY_STYLES: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const URGENCY_LABELS: Record<string, string> = {
  critical: "CRITIQUE",
  high: "ÉLEVÉE",
  medium: "MOYENNE",
  low: "FAIBLE",
};

export function PriorityBadge({ urgency }: { urgency: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border",
        URGENCY_STYLES[urgency] || URGENCY_STYLES.low
      )}
    >
      {URGENCY_LABELS[urgency] || urgency.toUpperCase()}
    </span>
  );
}
