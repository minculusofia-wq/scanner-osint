"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchItems,
  fetchBriefs,
  fetchStats,
  triggerCollection,
} from "@/lib/api";
import type {
  IntelligenceItem,
  IntelligenceBrief,
  IntelligenceStats,
} from "@/types/intelligence";

interface Filters {
  category?: string;
  urgency?: string;
  source?: string;
}

export function useIntelligence(autoRefresh = false) {
  const [items, setItems] = useState<IntelligenceItem[]>([]);
  const [briefs, setBriefs] = useState<IntelligenceBrief[]>([]);
  const [stats, setStats] = useState<IntelligenceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({});

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [itemsData, briefsData, statsData] = await Promise.all([
        fetchItems({ limit: 100, ...filters }),
        fetchBriefs({ limit: 30 }),
        fetchStats(),
      ]);
      setItems(itemsData);
      setBriefs(briefsData);
      setStats(statsData);
    } catch (e: any) {
      setError(e.message || "Failed to load intelligence data");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const collect = useCallback(async () => {
    setCollecting(true);
    try {
      await triggerCollection();
      await load();
    } catch (e: any) {
      setError(e.message || "Collection failed");
    } finally {
      setCollecting(false);
    }
  }, [load]);

  useEffect(() => {
    load();
    if (autoRefresh) {
      const interval = setInterval(load, 60000);
      return () => clearInterval(interval);
    }
  }, [load, autoRefresh]);

  return {
    items,
    briefs,
    stats,
    loading,
    collecting,
    error,
    refresh: load,
    collect,
    filters,
    setFilters,
  };
}
