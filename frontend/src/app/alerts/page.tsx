"use client";

import { useAlerts } from "@/hooks/useAlerts";
import { Header } from "@/components/layout/Header";
import { EscalationCard } from "@/components/EscalationCard";
import { AlertHistoryRow } from "@/components/AlertHistoryRow";
import Link from "next/link";

export default function AlertsPage() {
  const { escalations, history, loading, error, refresh } = useAlerts(true);

  const activeEscalations = escalations.filter(
    (e) => e.escalation_level !== "stable"
  );

  return (
    <div className="space-y-6">
      <Header
        title="Système d'alerte"
        subtitle="Détection prédictive multi-sources"
        action={
          <div className="flex gap-2">
            <Link
              href="/alerts/settings"
              className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium transition-colors"
            >
              Configuration
            </Link>
            <button
              onClick={refresh}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
            >
              Actualiser
            </button>
          </div>
        }
      />

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">Chargement...</p>
        </div>
      ) : (
        <>
          {/* Active Escalations */}
          <section>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Escalades actives ({activeEscalations.length})
            </h3>
            {activeEscalations.length === 0 ? (
              <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-8 text-center">
                <div className="text-3xl mb-2">&#x2705;</div>
                <p className="text-gray-400">
                  Aucune escalade active — tous les secteurs sont stables
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  Les escalades apparaissent quand plusieurs sources convergent
                  sur la même région
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {activeEscalations.map((tracker) => (
                  <EscalationCard key={tracker.id} tracker={tracker} />
                ))}
              </div>
            )}
          </section>

          {/* All Trackers */}
          {escalations.length > activeEscalations.length && (
            <section>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Suivis stables ({escalations.length - activeEscalations.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {escalations
                  .filter((e) => e.escalation_level === "stable")
                  .map((tracker) => (
                    <EscalationCard key={tracker.id} tracker={tracker} />
                  ))}
              </div>
            </section>
          )}

          {/* Alert History */}
          <section>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Historique des alertes ({history.length})
            </h3>
            {history.length === 0 ? (
              <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-6 text-center text-gray-500 text-sm">
                Aucune alerte envoyée pour le moment
              </div>
            ) : (
              <div className="rounded-xl border border-gray-800 bg-gray-900/60 divide-y divide-gray-800/50 px-4">
                {history.map((alert) => (
                  <AlertHistoryRow key={alert.id} alert={alert} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
