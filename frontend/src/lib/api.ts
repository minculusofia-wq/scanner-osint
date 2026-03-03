import axios from "axios";
import type {
  IntelligenceItem,
  IntelligenceBrief,
  IntelligenceStats,
  OSINTConfig,
} from "@/types/intelligence";

const api = axios.create({
  baseURL: "http://localhost:8001/api",
  timeout: 30000,
});

// Items
export const fetchItems = (params?: {
  limit?: number;
  offset?: number;
  category?: string;
  urgency?: string;
  source?: string;
  include_stale?: boolean;
}) =>
  api
    .get<IntelligenceItem[]>("/intelligence/items/", { params })
    .then((r) => r.data);

// Briefs
export const fetchBriefs = (params?: {
  limit?: number;
  actionable_only?: boolean;
}) =>
  api
    .get<IntelligenceBrief[]>("/intelligence/briefs/", { params })
    .then((r) => r.data);

export const dismissBrief = (briefId: number) =>
  api
    .post(`/intelligence/briefs/${briefId}/dismiss`)
    .then((r) => r.data);

// Collection
export const triggerCollection = () =>
  api
    .post<Record<string, number>>("/intelligence/collect", {}, { timeout: 120000 })
    .then((r) => r.data);

// Stats
export const fetchStats = () =>
  api.get<IntelligenceStats>("/intelligence/stats").then((r) => r.data);

// Config
export const fetchConfig = () =>
  api.get<OSINTConfig>("/intelligence/config").then((r) => r.data);

export const updateConfig = (data: Partial<OSINTConfig>) =>
  api.put<OSINTConfig>("/intelligence/config", data).then((r) => r.data);
