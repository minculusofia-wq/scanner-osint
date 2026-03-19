'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import KnowledgeGraph from '@/components/KnowledgeGraph';
import { useIntelligence } from '@/hooks/useIntelligence';
import { BriefCard } from '@/components/BriefCard';
import { SignalCard } from '@/components/SignalCard';

export default function GraphPage() {
  const { briefs, loading, refresh } = useIntelligence(true);
  const [selectedBriefId, setSelectedBriefId] = useState<number | null>(null);

  const selectedBrief = briefs.find(b => b.id === selectedBriefId) || briefs[0];

  useEffect(() => {
    if (!selectedBriefId && briefs.length > 0) {
      setSelectedBriefId(briefs[0].id);
    }
  }, [briefs, selectedBriefId]);

  return (
    <div className="space-y-6 h-full flex flex-col">
      <Header
        title="Analyse de Confluence (Link Analysis)"
        subtitle="Visualisation du Knowledge Graph Palantir"
        action={
          <button
            onClick={refresh}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
          >
            Actualiser
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1">
        {/* Sidebar: Brief List */}
        <div className="lg:col-span-1 space-y-4 overflow-y-auto max-h-[calc(100vh-250px)] pr-2">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Clusters d'Intelligence
          </h3>
          {briefs.map((brief) => (
            <div
              key={brief.id}
              onClick={() => setSelectedBriefId(brief.id)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedBriefId === brief.id
                  ? 'bg-indigo-600/10 border-indigo-500/50 ring-1 ring-indigo-500/20'
                  : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="text-[10px] font-bold text-indigo-400 uppercase">{brief.category}</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  brief.urgency === 'critical' ? 'bg-red-500/20 text-red-400' :
                  brief.urgency === 'high' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-slate-800 text-slate-400'
                }`}>
                  {brief.priority_score.toFixed(0)}
                </span>
              </div>
              <h4 className="text-sm font-medium text-slate-200 line-clamp-2">{brief.title}</h4>
            </div>
          ))}
        </div>

        {/* Main: Graph View */}
        <div className="lg:col-span-3 space-y-4">
          {loading ? (
            <div className="w-full h-[600px] flex items-center justify-center bg-slate-950 rounded-xl border border-slate-800">
              <div className="text-slate-500 animate-pulse">Génération du graphe...</div>
            </div>
          ) : selectedBrief && selectedBrief.graph_data && JSON.parse(selectedBrief.graph_data).nodes?.length > 0 ? (
            <KnowledgeGraph 
              data={JSON.parse(selectedBrief.graph_data)} 
              title={`Graphique pour: ${selectedBrief.title}`}
            />
          ) : (
            <div className="w-full h-[600px] flex flex-col items-center justify-center bg-slate-950 rounded-xl border border-slate-800 text-center p-8">
              <div className="text-4xl mb-4">🕸️</div>
              <h3 className="text-slate-300 font-medium mb-2">Pas encore de données de graphe</h3>
              <p className="text-slate-500 text-sm max-w-md">
                Lancez une nouvelle collecte pour générer les connexions d'entités Palantir pour ce cluster d'intelligence.
              </p>
            </div>
          )}

          {/* AI Insights Panel */}
          {selectedBrief && (
            <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
              <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
                <span className="text-indigo-400">✨</span> Analyse de Signal
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed italic">
                {selectedBrief.ai_analysis || selectedBrief.summary}
              </p>
              {selectedBrief.ai_trading_signal && (
                <div className="mt-3 p-2 bg-indigo-500/10 border border-indigo-500/20 rounded text-xs text-indigo-300">
                  <span className="font-bold">SIGNAL TRADING:</span> {selectedBrief.ai_trading_signal}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
