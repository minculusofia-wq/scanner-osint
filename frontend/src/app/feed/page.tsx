"use client";

import { useIntelligence } from "@/hooks/useIntelligence";
import { Header } from "@/components/layout/Header";
import { ItemCard } from "@/components/ItemCard";
import { Filters } from "@/components/Filters";

export default function FeedPage() {
  const { items, loading, error, filters, setFilters, refresh } =
    useIntelligence(true);

  return (
    <div className="space-y-6">
      <Header
        title="Flux brut"
        subtitle={`${items.length} éléments collectés`}
        action={
          <button
            onClick={refresh}
            className="px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
          >
            Actualiser
          </button>
        }
      />

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      <Filters filters={filters} onChange={setFilters} />

      {loading && items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">Chargement...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p>Aucun élément ne correspond à vos filtres</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
