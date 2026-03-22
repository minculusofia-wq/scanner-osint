"use client";

import { useEffect, useState } from "react";
import { fetchNotebookStatus, generateNotebookPodcast } from "@/lib/api";

export function NotebookLMControl() {
  const [status, setStatus] = useState<{ is_ready: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; notebook_url: string; message: string } | null>(null);

  const checkStatus = () => {
    fetchNotebookStatus().then(setStatus).catch(() => setStatus({ is_ready: false, message: "Erreur backend" }));
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await generateNotebookPodcast();
      setResult(res);
      if (res.success) {
        window.open(res.notebook_url, "_blank");
      }
    } catch (err: any) {
      setResult({ success: false, notebook_url: "", message: err.response?.data?.detail || "Erreur de génération" });
    } finally {
      setLoading(false);
    }
  };

  if (!status) return null;

  return (
    <div className="bg-gradient-to-br from-indigo-900/20 to-slate-900 border border-indigo-500/20 rounded-xl p-4 shadow-lg mb-6">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/30">
            <span className="text-2xl">🎙️</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-tight">Audio Intelligence (NotebookLM)</h3>
            <p className="text-xs text-slate-400 max-w-md">
              Générez un podcast "Deep Dive" personnalisé en français à partir de vos signaux Alpha.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!status.is_ready ? (
            <div className="text-right">
              <span className="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded font-mono block mb-1">
                Connexion requise
              </span>
              <p className="text-[10px] text-slate-500 max-w-[180px]">
                Lancez <code className="bg-slate-800 px-1 py-0.5 rounded">notebooklm login</code> dans votre terminal une fois.
              </p>
            </div>
          ) : (
            <>
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
              <button
                onClick={handleGenerate}
                disabled={loading}
                className={`px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-all shadow-md flex items-center gap-2 ${
                  loading ? "animate-pulse opacity-70 cursor-not-allowed" : ""
                }`}
              >
                {loading ? "Génération en cours..." : "Générer mon Podcast Alpha"}
              </button>
            </>
          )}
        </div>
      </div>
      
      {result && !result.success && (
        <div className="mt-3 text-xs text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
          ⚠️ {result.message}
        </div>
      )}
    </div>
  );
}
