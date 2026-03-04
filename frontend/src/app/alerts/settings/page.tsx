"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import {
  fetchAlertConfig,
  updateAlertConfig,
  sendTestAlert,
  fetchAlertRules,
  createAlertRule,
  deleteAlertRule,
} from "@/lib/api";
import type { AlertConfig, AlertRule } from "@/types/intelligence";
import Link from "next/link";

export default function AlertSettingsPage() {
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchAlertConfig(), fetchAlertRules()])
      .then(([cfg, rul]) => {
        setConfig(cfg);
        setRules(rul);
      })
      .catch(() => setError("Erreur de chargement"));
  }, []);

  const save = async (partial: Partial<AlertConfig>) => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await updateAlertConfig(partial);
      setConfig(updated);
    } catch {
      setError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await sendTestAlert();
      setTestResult("Alerte test envoyee !");
    } catch (e: any) {
      setTestResult(
        e?.response?.data?.detail || "Echec de l'envoi"
      );
    } finally {
      setTesting(false);
    }
  };

  const handleAddDefaultRule = async () => {
    try {
      const rule = await createAlertRule({
        name: "Alerte par defaut",
        description: "Alerte pour escalades elevated+",
        is_enabled: true,
        min_escalation_level: "elevated",
        min_priority_score: 40,
        min_signal_count: 3,
        min_unique_sources: 2,
        signal_window_minutes: 120,
        categories: [],
        regions: [],
        required_patterns: [],
        delivery_channels: ["discord"],
        cooldown_minutes: 30,
        max_alerts_per_hour: 5,
      });
      setRules((prev) => [rule, ...prev]);
    } catch {
      setError("Erreur lors de la creation de la regle");
    }
  };

  const handleDeleteRule = async (id: number) => {
    try {
      await deleteAlertRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError("Erreur lors de la suppression");
    }
  };

  if (!config) {
    return (
      <div className="text-center py-16 text-gray-500">Chargement...</div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <Header
        title="Configuration alertes"
        subtitle="Discord, regles, anti-spam"
        action={
          <Link
            href="/alerts"
            className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium transition-colors"
          >
            Retour
          </Link>
        }
      />

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Global toggle */}
      <section className="rounded-xl border border-gray-800 bg-gray-900/60 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Activation</h3>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.alerts_enabled}
            onChange={(e) => save({ alerts_enabled: e.target.checked })}
            className="w-5 h-5 rounded bg-gray-800 border-gray-600"
          />
          <span className="text-sm text-gray-300">
            Systeme d&apos;alerte actif
          </span>
        </label>
      </section>

      {/* Discord */}
      <section className="rounded-xl border border-indigo-500/30 bg-gray-900/60 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Discord</h3>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.discord_enabled}
            onChange={(e) => save({ discord_enabled: e.target.checked })}
            className="w-5 h-5 rounded bg-gray-800 border-gray-600"
          />
          <span className="text-sm text-gray-300">
            Alertes Discord activees
          </span>
        </label>
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Webhook URL
          </label>
          <input
            type="text"
            value={config.discord_webhook_url}
            onChange={(e) =>
              setConfig({ ...config, discord_webhook_url: e.target.value })
            }
            onBlur={() =>
              save({ discord_webhook_url: config.discord_webhook_url })
            }
            placeholder="https://discord.com/api/webhooks/..."
            className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white placeholder-gray-600 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <button
          onClick={handleTest}
          disabled={testing || !config.discord_webhook_url}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
        >
          {testing ? "Envoi..." : "Tester la connexion"}
        </button>
        {testResult && (
          <p className="text-xs text-gray-400">{testResult}</p>
        )}
      </section>

      {/* Anti-spam */}
      <section className="rounded-xl border border-gray-800 bg-gray-900/60 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Anti-spam</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Cooldown global (min)
            </label>
            <input
              type="number"
              value={config.global_cooldown_minutes}
              onChange={(e) =>
                setConfig({
                  ...config,
                  global_cooldown_minutes: parseInt(e.target.value) || 15,
                })
              }
              onBlur={() =>
                save({
                  global_cooldown_minutes: config.global_cooldown_minutes,
                })
              }
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Max alertes / heure
            </label>
            <input
              type="number"
              value={config.max_alerts_per_hour}
              onChange={(e) =>
                setConfig({
                  ...config,
                  max_alerts_per_hour: parseInt(e.target.value) || 10,
                })
              }
              onBlur={() =>
                save({ max_alerts_per_hour: config.max_alerts_per_hour })
              }
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Heures silencieuses debut (UTC, -1 = off)
            </label>
            <input
              type="number"
              value={config.quiet_hours_start}
              onChange={(e) =>
                setConfig({
                  ...config,
                  quiet_hours_start: parseInt(e.target.value),
                })
              }
              onBlur={() =>
                save({ quiet_hours_start: config.quiet_hours_start })
              }
              min={-1}
              max={23}
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Heures silencieuses fin (UTC)
            </label>
            <input
              type="number"
              value={config.quiet_hours_end}
              onChange={(e) =>
                setConfig({
                  ...config,
                  quiet_hours_end: parseInt(e.target.value),
                })
              }
              onBlur={() =>
                save({ quiet_hours_end: config.quiet_hours_end })
              }
              min={-1}
              max={23}
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>
      </section>

      {/* Rules */}
      <section className="rounded-xl border border-gray-800 bg-gray-900/60 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Regles d&apos;alerte ({rules.length})
          </h3>
          <button
            onClick={handleAddDefaultRule}
            className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition-colors"
          >
            + Ajouter regle par defaut
          </button>
        </div>
        {rules.length === 0 ? (
          <p className="text-xs text-gray-500">
            Aucune regle configuree. Une regle par defaut (elevated+) sera
            utilisee automatiquement.
          </p>
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700/50"
              >
                <div>
                  <div className="text-sm text-white font-medium">
                    {rule.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Min: {rule.min_escalation_level} | Signaux:{" "}
                    {rule.min_signal_count}+ | Sources:{" "}
                    {rule.min_unique_sources}+ | Cooldown:{" "}
                    {rule.cooldown_minutes}min
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      rule.is_enabled ? "bg-green-500" : "bg-gray-600"
                    }`}
                  />
                  {rule.id && (
                    <button
                      onClick={() => handleDeleteRule(rule.id!)}
                      className="text-xs text-red-500 hover:text-red-400"
                    >
                      Supprimer
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
