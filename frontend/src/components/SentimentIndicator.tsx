import { cn } from "@/lib/utils";

export function SentimentIndicator({ score }: { score: number }) {
  let color = "bg-gray-500";
  let label = "Neutre";

  if (score > 0.3) {
    color = "bg-green-500";
    label = "Positif";
  } else if (score > 0.1) {
    color = "bg-green-400";
    label = "Légèrement +";
  } else if (score < -0.3) {
    color = "bg-red-500";
    label = "Négatif";
  } else if (score < -0.1) {
    color = "bg-red-400";
    label = "Légèrement -";
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className={cn("w-2 h-2 rounded-full", color)} />
      <span className="text-xs text-gray-400">
        {label} ({score > 0 ? "+" : ""}
        {score.toFixed(2)})
      </span>
    </div>
  );
}
