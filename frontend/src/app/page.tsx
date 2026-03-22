"use client";

import { useEffect, useState } from "react";
import { useIntelligence } from "@/hooks/useIntelligence";
import { Header } from "@/components/layout/Header";
import { StatsBar } from "@/components/StatsBar";
import { BriefCard } from "@/components/BriefCard";
import { SignalCard } from "@/components/SignalCard";
import { ItemCard } from "@/components/ItemCard";
import { EscalationCard } from "@/components/EscalationCard";
import { dismissBrief, fetchEscalations } from "@/lib/api";
import { NotebookLMControl } from "@/components/NotebookLMControl";
import type { EscalationTracker } from "@/types/intelligence";
import Link from "next/link";

export default function DashboardPage() {
  const { items, briefs, stats, loading, collecting, error, collect, refresh } =
    useIntelligence(true);

  const [escalations, setEscalations] = useState<EscalationTracker[]>([]);
  useEffect(() => {
    fetchEscalations().then(setEscalations).catch(() => {});
    const iv = setInterval(() => {
      fetchEscalations().then(setEscalations).catch(() => {});
    }, 30000);
    return () => clearInterval(iv);
  }, []);

  const activeEscalations = escalations.filter(
    (e) => e.escalation_level !== "stable"
  );
  const actionableBriefs = briefs.filter((b) => b.is_actionable);
  const topItems = items.filter((i) => i.urgency === "critical" || i.urgency === "high").slice(0, 10);

  const handleDismiss = async (id: number) => {
    await dismissBrief(id);
    refresh();
  };

  return (
    <div className="space-y-6">
      <Header
        title="Tableau de bord"
        subtitle="Renseignement OSINT en temps réel"
        action={
          <button
            onClick={collect}
            disabled={collecting}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
          >
            {collecting ? "Collecte en cours..." : "Collecter"}
          </button>
        }
      />

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Stats */}
      <StatsBar stats={stats} />

      {loading && items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">📡</div>
          <p className="text-lg">Chargement des données...</p>
          <p className="text-sm mt-1">Vérifiez que le backend tourne sur le port 8001</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-lg">Aucune donnée pour le moment</p>
          <p className="text-sm mt-1">
            Cliquez sur &quot;Collecter&quot; pour lancer la collecte OSINT
          </p>
        </div>
      ) : (
        <>
          {/* NotebookLM Export */}
          <NotebookLMControl />

          {/* Escalation Banner */}
          {activeEscalations.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-red-500 uppercase tracking-wider">
                  🚨 Alertes d'Escalade ({activeEscalations.length})
                </h3>
                <Link
                  href="/alerts"
                  className="text-xs text-indigo-400 hover:text-indigo-300"
                >
                  Voir tout
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {activeEscalations.slice(0, 3).map((tracker) => (
                  <EscalationCard key={tracker.id} tracker={tracker} />
                ))}
              </div>
            </section>
          )}

          {/* Actionable Signals (The Edge) */}
          {actionableBriefs.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                  ✨ Alpha & Informations Privilégiées ({actionableBriefs.length})
                </h3>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {actionableBriefs.map((brief) => (
                  <BriefCard
                    key={brief.id}
                    brief={brief}
                    onDismiss={handleDismiss}
                  />
                ))}
              </div>
            </section>
          )}

          {/* All Briefs */}
          {briefs.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Radar d'Intelligence (Signaux en formation)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {briefs.filter(b => !b.is_actionable).map((brief) => (
                  <SignalCard key={brief.id} brief={brief} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
