import axios from "axios";
import type {
  IntelligenceItem,
  IntelligenceBrief,
  IntelligenceStats,
  OSINTConfig,
  EscalationTracker,
  AlertHistoryEntry,
  AlertRule,
  AlertConfig,
  PrecursorPattern,
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

// --- AI Chat ---
export interface ChatMessage {
  role: "user" | "model";
  content: string;
}

export const chatWithAI = (message: string, history: ChatMessage[]) =>
  api
    .post<{ response: string }>("/intelligence/chat", { message, history })
    .then((r) => r.data.response);

// --- Alerts / Early Warning ---

export const fetchEscalations = (activeOnly = true) =>
  api
    .get<EscalationTracker[]>("/alerts/escalations", {
      params: { active_only: activeOnly },
    })
    .then((r) => r.data);

export const fetchAlertHistory = (params?: {
  limit?: number;
  offset?: number;
}) =>
  api
    .get<{ items: AlertHistoryEntry[]; total: number }>("/alerts/history", {
      params,
    })
    .then((r) => r.data);

export const fetchAlertRules = () =>
  api.get<AlertRule[]>("/alerts/rules").then((r) => r.data);

export const createAlertRule = (data: Omit<AlertRule, "id">) =>
  api.post<AlertRule>("/alerts/rules", data).then((r) => r.data);

export const updateAlertRule = (id: number, data: Omit<AlertRule, "id">) =>
  api.put<AlertRule>(`/alerts/rules/${id}`, data).then((r) => r.data);

export const deleteAlertRule = (id: number) =>
  api.delete(`/alerts/rules/${id}`).then((r) => r.data);

export const fetchAlertConfig = () =>
  api.get<AlertConfig>("/alerts/config").then((r) => r.data);

export const updateAlertConfig = (data: Partial<AlertConfig>) =>
  api.put<AlertConfig>("/alerts/config", data).then((r) => r.data);

export const sendTestAlert = () =>
  api.post("/alerts/test").then((r) => r.data);

export const fetchPatterns = () =>
  api.get<PrecursorPattern[]>("/alerts/patterns").then((r) => r.data);
