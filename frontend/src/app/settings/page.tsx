"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { fetchConfig, updateConfig, triggerCollection } from "@/lib/api";
import type { OSINTConfig } from "@/types/intelligence";

export default function SettingsPage() {
  const [config, setConfig] = useState<OSINTConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [message, setMessage] = useState("");

  const loadConfig = useCallback(async () => {
    try {
      const data = await fetchConfig();
      setConfig(data);
    } catch {
      setMessage("Échec du chargement de la configuration");
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const save = async (updates: Partial<OSINTConfig>) => {
    setSaving(true);
    try {
      const data = await updateConfig(updates);
      setConfig(data);
      setMessage("Sauvegardé !");
      setTimeout(() => setMessage(""), 2000);
    } catch {
      setMessage("Échec de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleCollect = async () => {
    setCollecting(true);
    try {
      const stats = await triggerCollection();
      setMessage(
        `Collecté ! ${stats.new || 0} nouveaux éléments, ${stats.briefs_generated || 0} résumés`
      );
      setTimeout(() => setMessage(""), 5000);
    } catch {
      setMessage("Échec de la collecte");
    } finally {
      setCollecting(false);
    }
  };

  if (!config) {
    return (
      <div className="text-center py-16 text-gray-500">Chargement des paramètres...</div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Header title="Paramètres" subtitle="Configuration du scanner OSINT" />

      {message && (
        <div className="rounded-lg bg-indigo-500/10 border border-indigo-500/30 px-4 py-2 text-indigo-400 text-sm">
          {message}
        </div>
      )}

      {/* General */}
      <section className="rounded-lg bg-gray-900 border border-gray-800 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Général</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-white">Collecte automatique</div>
            <div className="text-xs text-gray-500">
              Collecter le renseignement automatiquement en arrière-plan
            </div>
          </div>
          <button
            onClick={() => save({ enabled: !config.enabled })}
            className={`w-12 h-6 rounded-full transition-colors ${
              config.enabled ? "bg-indigo-600" : "bg-gray-700"
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full transition-transform mx-0.5 ${
                config.enabled ? "translate-x-6" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        <div>
          <label className="text-xs text-gray-400">
            Intervalle de collecte (secondes)
          </label>
          <input
            type="number"
            min={60}
            value={config.collection_interval_seconds}
            onChange={(e) =>
              setConfig({
                ...config,
                collection_interval_seconds: parseInt(e.target.value) || 600,
              })
            }
            onBlur={() =>
              save({
                collection_interval_seconds:
                  config.collection_interval_seconds,
              })
            }
            className="block w-full mt-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          />
        </div>

        <button
          onClick={handleCollect}
          disabled={collecting}
          className="w-full px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
        >
          {collecting ? "Collecte en cours..." : "Collecter maintenant (Manuel)"}
        </button>
      </section>

      {/* News/Data Sources */}
      <section className="rounded-lg bg-gray-900 border border-gray-800 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Sources d'actualités / données</h3>

        {[
          {
            key: "gdelt_enabled" as const,
            label: "GDELT",
            desc: "Événements mondiaux (gratuit, sans clé)",
            needsKey: false,
          },
          {
            key: "newsdata_enabled" as const,
            label: "NewsData.io",
            desc: "Articles d'actualité (gratuit : 200 crédits/jour)",
            needsKey: true,
            keyField: "newsdata_api_key" as const,
          },
          {
            key: "acled_enabled" as const,
            label: "ACLED",
            desc: "Données de conflits armés (gratuit avec inscription)",
            needsKey: true,
            keyField: "acled_api_key" as const,
            extraField: "acled_email" as const,
          },
          {
            key: "finnhub_enabled" as const,
            label: "Finnhub",
            desc: "Actualités marchés et calendrier éco (gratuit : 60 appels/min)",
            needsKey: true,
            keyField: "finnhub_api_key" as const,
          },
          {
            key: "reddit_enabled" as const,
            label: "Reddit",
            desc: "Subreddits marchés prédictifs et géopolitique (gratuit)",
            needsKey: false,
          },
        ].map((source) => (
          <div key={source.key} className="border-b border-gray-800 pb-4 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm text-white">{source.label}</div>
                <div className="text-xs text-gray-500">{source.desc}</div>
              </div>
              <button
                onClick={() => save({ [source.key]: !config[source.key] })}
                className={`w-12 h-6 rounded-full transition-colors ${
                  config[source.key] ? "bg-indigo-600" : "bg-gray-700"
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform mx-0.5 ${
                    config[source.key] ? "translate-x-6" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {source.needsKey && source.keyField && (
              <div className="mt-2">
                <input
                  type="password"
                  placeholder="Clé API"
                  value={config[source.keyField] || ""}
                  onChange={(e) =>
                    setConfig({ ...config, [source.keyField!]: e.target.value })
                  }
                  onBlur={() =>
                    save({ [source.keyField!]: config[source.keyField!] })
                  }
                  className="block w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {source.extraField && (
              <div className="mt-2">
                <input
                  type="text"
                  placeholder="Email (requis pour ACLED)"
                  value={config[source.extraField] || ""}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      [source.extraField!]: e.target.value,
                    })
                  }
                  onBlur={() =>
                    save({
                      [source.extraField!]: config[source.extraField!],
                    })
                  }
                  className="block w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}
          </div>
        ))}
      </section>

      {/* FININT */}
      <section className="rounded-lg bg-gray-900 border border-yellow-800/50 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-yellow-400">FININT (Renseignement financier)</h3>

        {[
          {
            key: "sec_edgar_enabled" as const,
            label: "SEC EDGAR",
            desc: "Déclarations SEC : 8-K, Form 4 délits d'initiés (gratuit)",
            needsKey: false,
          },
          {
            key: "whale_crypto_enabled" as const,
            label: "Whale Crypto",
            desc: "Grosses TX ETH des exchanges/whales (Etherscan)",
            needsKey: true,
            keyField: "etherscan_api_key" as const,
          },
          {
            key: "fred_enabled" as const,
            label: "FRED",
            desc: "Données Fed : PIB, IPC, chômage, taux directeurs",
            needsKey: true,
            keyField: "fred_api_key" as const,
          },
        ].map((source) => (
          <div key={source.key} className="border-b border-gray-800 pb-4 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm text-white">{source.label}</div>
                <div className="text-xs text-gray-500">{source.desc}</div>
              </div>
              <button
                onClick={() => save({ [source.key]: !config[source.key] })}
                className={`w-12 h-6 rounded-full transition-colors ${
                  config[source.key] ? "bg-yellow-600" : "bg-gray-700"
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform mx-0.5 ${
                    config[source.key] ? "translate-x-6" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
            {source.needsKey && source.keyField && (
              <div className="mt-2">
                <input
                  type="password"
                  placeholder="Clé API"
                  value={config[source.keyField] || ""}
                  onChange={(e) =>
                    setConfig({ ...config, [source.keyField!]: e.target.value })
                  }
                  onBlur={() =>
                    save({ [source.keyField!]: config[source.keyField!] })
                  }
                  className="block w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-yellow-500"
                />
              </div>
            )}
          </div>
        ))}
      </section>

      {/* GEOINT */}
      <section className="rounded-lg bg-gray-900 border border-sky-800/50 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-sky-400">GEOINT (Renseignement géospatial)</h3>

        {[
          {
            key: "adsb_enabled" as const,
            label: "OpenSky ADS-B",
            desc: "Suivi d'avions militaires/gouvernementaux (gratuit)",
          },
          {
            key: "nasa_firms_enabled" as const,
            label: "NASA FIRMS",
            desc: "Détection satellite d'incendies/thermique en zones de conflit (gratuit)",
          },
          {
            key: "ship_tracker_enabled" as const,
            label: "Ship Tracker",
            desc: "Activité maritime dans les détroits stratégiques (gratuit)",
          },
        ].map((source) => (
          <div key={source.key} className="border-b border-gray-800 pb-4 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm text-white">{source.label}</div>
                <div className="text-xs text-gray-500">{source.desc}</div>
              </div>
              <button
                onClick={() => save({ [source.key]: !config[source.key] })}
                className={`w-12 h-6 rounded-full transition-colors ${
                  config[source.key] ? "bg-sky-600" : "bg-gray-700"
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform mx-0.5 ${
                    config[source.key] ? "translate-x-6" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>
        ))}
      </section>

      {/* Social OSINT */}
      <section className="rounded-lg bg-gray-900 border border-blue-800/50 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-blue-400">OSINT Social</h3>

        {[
          {
            key: "telegram_enabled" as const,
            label: "Telegram",
            desc: "Canaux OSINT publics (intel_slava, CIG, Rybar...)",
          },
          {
            key: "gov_rss_enabled" as const,
            label: "RSS Gouvernements",
            desc: "Maison Blanche, DoD, Dept. d'État, UE, OTAN, ONU",
          },
        ].map((source) => (
          <div key={source.key} className="border-b border-gray-800 pb-4 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm text-white">{source.label}</div>
                <div className="text-xs text-gray-500">{source.desc}</div>
              </div>
              <button
                onClick={() => save({ [source.key]: !config[source.key] })}
                className={`w-12 h-6 rounded-full transition-colors ${
                  config[source.key] ? "bg-blue-600" : "bg-gray-700"
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform mx-0.5 ${
                    config[source.key] ? "translate-x-6" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>
        ))}
      </section>

      {/* Filtering */}
      <section className="rounded-lg bg-gray-900 border border-gray-800 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Filtrage</h3>

        <div>
          <label className="text-xs text-gray-400">
            Score de priorité minimum (0 = tout afficher)
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={config.min_priority_score}
            onChange={(e) =>
              setConfig({
                ...config,
                min_priority_score: parseFloat(e.target.value) || 0,
              })
            }
            onBlur={() =>
              save({ min_priority_score: config.min_priority_score })
            }
            className="block w-full mt-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="text-xs text-gray-400">
            Obsolète après (heures, 0 = jamais)
          </label>
          <input
            type="number"
            min={0}
            value={config.stale_after_hours}
            onChange={(e) =>
              setConfig({
                ...config,
                stale_after_hours: parseInt(e.target.value) || 48,
              })
            }
            onBlur={() =>
              save({ stale_after_hours: config.stale_after_hours })
            }
            className="block w-full mt-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          />
        </div>
      </section>
    </div>
  );
}
