import type { AlertHistoryEntry } from "@/types/intelligence";
import { EscalationLevelBadge } from "./EscalationLevelBadge";
import type { EscalationLevel } from "@/types/intelligence";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AlertHistoryRow({ alert }: { alert: AlertHistoryEntry }) {
  return (
    <div className="flex items-start gap-4 py-3 border-b border-gray-800/50 last:border-0">
      {/* Level badge */}
      <div className="pt-0.5">
        <EscalationLevelBadge
          level={(alert.escalation_level || alert.severity) as EscalationLevel}
          size="sm"
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-white truncate">
          {alert.title}
        </h4>
        <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
          {alert.message}
        </p>
        <div className="flex items-center gap-3 mt-1.5 text-[10px] text-gray-500">
          {alert.region && (
            <span>{alert.region.replace("_", " ")}</span>
          )}
          {alert.trigger_signal_count > 0 && (
            <span>{alert.trigger_signal_count} signaux</span>
          )}
          {alert.matched_patterns.length > 0 && (
            <span>{alert.matched_patterns.join(", ")}</span>
          )}
        </div>
      </div>

      {/* Channel + time */}
      <div className="text-right shrink-0">
        <div className="flex gap-1 justify-end">
          {alert.channels_sent.map((ch) => (
            <span
              key={ch}
              className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-500/10 text-indigo-400"
            >
              {ch}
            </span>
          ))}
        </div>
        <div className="text-[10px] text-gray-600 mt-1">
          {formatDate(alert.created_at)}
        </div>
        <div
          className={`text-[10px] mt-0.5 ${
            alert.delivery_status === "sent"
              ? "text-green-500"
              : "text-red-500"
          }`}
        >
          {alert.delivery_status}
        </div>
      </div>
    </div>
  );
}
