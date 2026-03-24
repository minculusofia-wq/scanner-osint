"use client";

import { useEffect, useState } from "react";
import { fetchNotebookStatus, generateNotebookPodcast, generateNotebookMindMap, generateNotebookDataTable } from "@/lib/api";

export function NotebookLMControl() {
  const [status, setStatus] = useState<{ is_ready: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<{ success: boolean; notebook_url?: string; message: string } | null>(null);

  useEffect(() => {
    fetchNotebookStatus().then(setStatus).catch(() => setStatus({ is_ready: false, message: "Erreur backend" }));
  }, []);

  const handleAction = async (action: string) => {
    setLoading(action);
    setResult(null);
    try {
      if (action === "podcast") {
        const res = await generateNotebookPodcast();
        setResult(res);
        if (res.success && res.notebook_url) window.open(res.notebook_url, "_blank");
      } else if (action === "mindmap") {
        const res = await generateNotebookMindMap();
        setResult({ success: res.success, message: res.message });
      } else if (action === "csv") {
        await generateNotebookDataTable();
        setResult({ success: true, message: "CSV téléchargé avec succès." });
      }
    } catch (err: any) {
      setResult({ success: false, message: err.response?.data?.detail || "Erreur de génération" });
    } finally {
      setLoading(null);
    }
  };

  if (!status) return null;

  return (
    <div className="bg-gradient-to-br from-indigo-900/20 to-slate-900 border border-indigo-500/20 rounded-xl p-4 shadow-lg mb-6">
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/30">
            <span className="text-2xl">🎙️</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-tight">NotebookLM Studio</h3>
            <p className="text-xs text-slate-400 max-w-md">
              Générez des podcasts, mind maps et exports CSV à partir de vos signaux Alpha.
            </p>
          </div>
        </div>

        {/* Actions */}
        {!status.is_ready ? (
          <div className="flex items-center gap-2">
            <span className="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded font-mono">
              Connexion requise
            </span>
            <p className="text-[10px] text-slate-500">
              Lancez <code className="bg-slate-800 px-1 py-0.5 rounded">notebooklm login</code> dans votre terminal.
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            {/* Podcast */}
            <button
              onClick={() => handleAction("podcast")}
              disabled={loading !== null}
              className={`px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-all shadow-md flex items-center gap-2 ${
                loading === "podcast" ? "animate-pulse opacity-70 cursor-not-allowed" : ""
              } ${loading && loading !== "podcast" ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              🎙️ {loading === "podcast" ? "Génération..." : "Podcast Alpha"}
            </button>

            {/* Mind Map */}
            <button
              onClick={() => handleAction("mindmap")}
              disabled={loading !== null}
              className={`px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium transition-all shadow-md flex items-center gap-2 ${
                loading === "mindmap" ? "animate-pulse opacity-70 cursor-not-allowed" : ""
              } ${loading && loading !== "mindmap" ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              🧠 {loading === "mindmap" ? "Génération..." : "Mind Map"}
            </button>

            {/* CSV Export */}
            <button
              onClick={() => handleAction("csv")}
              disabled={loading !== null}
              className={`px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium transition-all shadow-md flex items-center gap-2 ${
                loading === "csv" ? "animate-pulse opacity-70 cursor-not-allowed" : ""
              } ${loading && loading !== "csv" ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              📊 {loading === "csv" ? "Export..." : "Export CSV"}
            </button>

            {/* Notebook link */}
            {result?.notebook_url && (
              <a
                href={result.notebook_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs font-medium border border-emerald-500/30 transition-all"
              >
                Ouvrir Notebook ↗
              </a>
            )}
          </div>
        )}

        {/* Result message */}
        {result && (
          <div
            className={`text-xs p-2 rounded border ${
              result.success
                ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                : "text-red-400 bg-red-500/10 border-red-500/20"
            }`}
          >
            {result.success ? "✓" : "⚠️"} {result.message}
          </div>
        )}
      </div>
    </div>
  );
}
