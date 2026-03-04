"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchEscalations,
  fetchAlertHistory,
  fetchAlertRules,
  fetchAlertConfig,
} from "@/lib/api";
import { playAlertForLevel } from "@/lib/alertSound";
import type {
  EscalationTracker,
  AlertHistoryEntry,
  AlertRule,
  AlertConfig,
  EscalationLevel,
} from "@/types/intelligence";

const ALERT_LEVELS = new Set<EscalationLevel>(["elevated", "critical", "crisis"]);

export function useAlerts(autoRefresh = false) {
  const [escalations, setEscalations] = useState<EscalationTracker[]>([]);
  const [history, setHistory] = useState<AlertHistoryEntry[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track previous escalation state for sound alerts
  const prevEscalationsRef = useRef<Map<number, EscalationLevel>>(new Map());
  const isFirstLoad = useRef(true);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [esc, hist, rul, cfg] = await Promise.all([
        fetchEscalations().catch(() => []),
        fetchAlertHistory({ limit: 50 }).catch(() => ({
          items: [],
          total: 0,
        })),
        fetchAlertRules().catch(() => []),
        fetchAlertConfig().catch(() => null),
      ]);

      // Sound alert: detect new or upgraded escalations
      if (!isFirstLoad.current && esc.length > 0) {
        const prev = prevEscalationsRef.current;
        let highestNewLevel: EscalationLevel | null = null;

        for (const tracker of esc) {
          const level = tracker.escalation_level;
          if (!ALERT_LEVELS.has(level)) continue;

          const prevLevel = prev.get(tracker.id);
          const isNew = !prevLevel;
          const isUpgrade = prevLevel && level !== prevLevel &&
            levelIndex(level) > levelIndex(prevLevel);

          if (isNew || isUpgrade) {
            if (!highestNewLevel || levelIndex(level) > levelIndex(highestNewLevel)) {
              highestNewLevel = level;
            }
          }
        }

        if (highestNewLevel) {
          playAlertForLevel(highestNewLevel);
        }
      }

      // Update prev state
      const newMap = new Map<number, EscalationLevel>();
      for (const t of esc) {
        newMap.set(t.id, t.escalation_level);
      }
      prevEscalationsRef.current = newMap;
      isFirstLoad.current = false;

      setEscalations(esc);
      setHistory(hist.items);
      setHistoryTotal(hist.total);
      setRules(rul);
      if (cfg) setConfig(cfg);
    } catch (e) {
      setError("Erreur de chargement des alertes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    if (!autoRefresh) return;
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh, autoRefresh]);

  return {
    escalations,
    history,
    historyTotal,
    rules,
    config,
    loading,
    error,
    refresh,
  };
}

function levelIndex(level: EscalationLevel): number {
  const levels: EscalationLevel[] = ["stable", "concerning", "elevated", "critical", "crisis"];
  return levels.indexOf(level);
}
