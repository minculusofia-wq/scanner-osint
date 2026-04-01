'use client';

import React, { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Panel,
  Node,
  Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface GraphData {
  nodes: any[];
  edges: any[];
}

interface KnowledgeGraphProps {
  data: GraphData;
  title?: string;
}

const nodeColors: Record<string, string> = {
  event: '#3b82f6', // blue
  person: '#ec4899', // pink
  organization: '#f59e0b', // amber
  location: '#10b981', // emerald
  asset: '#8b5cf6', // violet
  geopolitical: '#64748b', // slate
};

export default function KnowledgeGraph({ data, title }: KnowledgeGraphProps) {
  const initialNodes: Node[] = useMemo(() => {
    return (data.nodes ?? []).map((n, i) => ({
      id: n.id,
      data: { label: n.label || n.id },
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      style: {
        background: nodeColors[n.type] || '#fff',
        color: '#fff',
        borderRadius: '8px',
        padding: '10px',
        fontSize: '12px',
        fontWeight: 'bold',
        width: 120,
        textAlign: 'center',
        border: 'none',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      },
      type: 'default',
    }));
  }, [data.nodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return (data.edges ?? []).map((e, i) => ({
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      label: e.type,
      animated: true,
      style: { stroke: '#94a3b8' },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#94a3b8',
      },
    }));
  }, [data.edges]);

  return (
    <div className="w-full h-[600px] border border-slate-800 rounded-xl overflow-hidden bg-slate-950 relative">
      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        fitView
        colorMode="dark"
      >
        <Background color="#334155" gap={20} />
        <Controls />
        {title && (
          <Panel position="top-left" className="bg-slate-900/80 p-2 rounded-lg border border-slate-700 text-slate-200 text-sm font-medium">
            {title}
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
