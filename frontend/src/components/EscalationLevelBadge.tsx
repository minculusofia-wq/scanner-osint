import { cn } from "@/lib/utils";
import type { EscalationLevel } from "@/types/intelligence";

const LEVEL_STYLES: Record<
  EscalationLevel,
  { bg: string; text: string; border: string; pulse?: boolean }
> = {
  stable: {
    bg: "bg-green-500/10",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  concerning: {
    bg: "bg-yellow-500/10",
    text: "text-yellow-400",
    border: "border-yellow-500/30",
  },
  elevated: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
    pulse: true,
  },
  crisis: {
    bg: "bg-red-700/20",
    text: "text-red-300",
    border: "border-red-600/50",
    pulse: true,
  },
};

const LEVEL_LABELS: Record<EscalationLevel, string> = {
  stable: "Stable",
  concerning: "Surveiller",
  elevated: "Élevé",
  critical: "Critique",
  crisis: "Crise",
};

export function EscalationLevelBadge({
  level,
  score,
  size = "md",
}: {
  level: EscalationLevel;
  score?: number;
  size?: "sm" | "md" | "lg";
}) {
  const style = LEVEL_STYLES[level] || LEVEL_STYLES.stable;
  const label = LEVEL_LABELS[level] || level;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        style.bg,
        style.text,
        style.border,
        style.pulse && "animate-pulse",
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-3 py-1 text-xs",
        size === "lg" && "px-4 py-1.5 text-sm"
      )}
    >
      <span
        className={cn(
          "rounded-full",
          style.text.replace("text-", "bg-"),
          size === "sm" && "w-1.5 h-1.5",
          size === "md" && "w-2 h-2",
          size === "lg" && "w-2.5 h-2.5"
        )}
      />
      {label}
      {score !== undefined && (
        <span className="opacity-70">({Math.round(score)})</span>
      )}
    </span>
  );
}
