import { ElementDatum, Graph, IElementEvent } from '@antv/g6';
import isEmpty from 'lodash/isEmpty';
import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from 'react';
import { buildNodesAndCombos } from './util';

import styles from './index.less';

// Entity type color palette
const ENTITY_COLORS = [
  '#5B8FF9', '#61DDAA', '#F6903D', '#F08BB4', '#7262FD',
  '#78D3F8', '#9661BC', '#F6C022', '#6DC8EC', '#E86452',
  '#63B2D4', '#FAAD14', '#5AD8A6', '#FF99C3', '#6395FA',
];

const ForceGraph = forwardRef<
  { focusNode: (nodeId: string) => void },
  {
    data: any;
    show: boolean;
    filterEntityTypes?: string[];
    filterRelationTypes?: string[];
    onNodeClick?: (node: any) => void;
    onEdgeClick?: (edge: any) => void;
  }
>(({ data, show, filterEntityTypes, filterRelationTypes, onNodeClick, onEdgeClick }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useImperativeHandle(ref, () => ({
    focusNode: (nodeId: string) => {
      if (graphRef.current) {
        graphRef.current.focusElement(nodeId, { duration: 500 });
      }
    },
  }));

  // Build entity type -> color map
  const entityColorMap = useMemo(() => {
    if (!data?.nodes) return {};
    const types = new Set<string>();
    data.nodes.forEach((n: any) => {
      if (n.entity_type) types.add((n.entity_type || '').replace(/"/g, ''));
    });
    const map: Record<string, string> = {};
    Array.from(types).forEach((t, i) => {
      map[t] = ENTITY_COLORS[i % ENTITY_COLORS.length];
    });
    return map;
  }, [data]);

  const filteredData = useMemo(() => {
    if (!isEmpty(data)) {
      let nodes = data.nodes || [];
      let edges = data.edges || [];

      if (filterEntityTypes && filterEntityTypes.length > 0) {
        nodes = nodes.filter(
          (n: any) =>
            !n.entity_type ||
            filterEntityTypes.includes((n.entity_type || '').replace(/"/g, '')),
        );
        const nodeIdSet = new Set(nodes.map((n: any) => n.id));
        edges = edges.filter(
          (e: any) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target),
        );
      }

      if (filterRelationTypes && filterRelationTypes.length > 0) {
        edges = edges.filter((e: any) => {
          const desc = (e.description || '').replace(/"/g, '').trim();
          return filterRelationTypes.includes(desc);
        });
        const connectedNodeIds = new Set<string>();
        edges.forEach((e: any) => {
          connectedNodeIds.add(e.source);
          connectedNodeIds.add(e.target);
        });
        nodes = nodes.filter((n: any) => connectedNodeIds.has(n.id));
      }

      const mi = buildNodesAndCombos(nodes);
      return { edges, ...mi };
    }
    return { nodes: [], edges: [] };
  }, [data, filterEntityTypes, filterRelationTypes]);

  const render = useCallback(() => {
    if (graphRef.current) {
      try { graphRef.current.destroy(); } catch (_) { /* ignore */ }
      graphRef.current = null;
    }

    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const hasCombos = filteredData.combos && filteredData.combos.length > 0;

    const graph = new Graph({
      container: containerRef.current,
      autoFit: 'view',
      autoResize: true,
      animation: true,
      behaviors: [
        'drag-element',
        'drag-canvas',
        'zoom-canvas',
        {
          type: 'hover-activate',
          degree: 1,
        },
      ],
      plugins: [
        {
          type: 'tooltip',
          enterable: true,
          getContent: (_e: IElementEvent, items: ElementDatum) => {
            if (Array.isArray(items)) {
              if (items.some((x) => x?.isCombo)) {
                return `<p style="font-weight:600;color:#5B8FF9">${items?.[0]?.data?.label}</p>`;
              }
              let result = '';
              items.forEach((item) => {
                const type = ((item as any)?.entity_type || '').replace(/"/g, '');
                const color = entityColorMap[type] || '#333';
                result += `<div style="max-width:320px;padding:4px 0">`;
                result += `<div style="font-weight:600;font-size:14px;margin-bottom:4px">${item?.id}</div>`;
                if (type) {
                  result += `<div style="margin-bottom:2px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px"></span><span style="color:#666;font-size:12px">${type}</span></div>`;
                }
                if ((item as any)?.description) {
                  result += `<div style="color:#888;font-size:12px;margin-top:4px;line-height:1.4">${((item as any).description || '').replace(/"/g, '').slice(0, 200)}</div>`;
                }
                result += '</div>';
              });
              return result;
            }
            return undefined;
          },
        },
      ],
      layout: hasCombos
        ? {
            type: 'combo-combined',
            preventOverlap: true,
            comboPadding: 1,
            spacing: 40,
          }
        : {
            type: 'd3-force',
            preventOverlap: true,
            nodeSize: 36,
            alphaDecay: 0.01,
            alphaMin: 0.001,
            collide: {
              radius: 40,
              strength: 0.8,
            },
            manyBody: {
              strength: -200,
            },
            link: {
              distance: 120,
            },
          },
      node: {
        style: {
          size: (d: any) => {
            const pr = d?.pagerank || 0;
            return Math.max(20, Math.min(60, 20 + pr * 400));
          },
          labelText: (d: any) => {
            const name = (d.id || '').replace(/"/g, '');
            return name.length > 8 ? name.slice(0, 8) + '...' : name;
          },
          labelFontSize: 11,
          labelPlacement: 'bottom',
          labelFill: '#333',
          labelBackground: true,
          labelBackgroundFill: 'rgba(255,255,255,0.85)',
          labelBackgroundRadius: 3,
          labelBackgroundLineWidth: 0,
          fill: (d: any) => {
            const type = ((d?.entity_type || '') as string).replace(/"/g, '');
            return entityColorMap[type] || '#5B8FF9';
          },
          stroke: (d: any) => {
            const type = ((d?.entity_type || '') as string).replace(/"/g, '');
            return entityColorMap[type] || '#5B8FF9';
          },
          lineWidth: 1.5,
          fillOpacity: 0.85,
          shadowColor: 'rgba(0,0,0,0.08)',
          shadowBlur: 8,
          shadowOffsetX: 2,
          shadowOffsetY: 2,
        },
        state: {
          active: {
            stroke: '#000',
            lineWidth: 2,
            fillOpacity: 1,
            labelFontWeight: 'bold',
          },
          inactive: {
            fillOpacity: 0.3,
            labelOpacity: 0.4,
          },
        },
      },
      edge: {
        style: {
          stroke: '#C2C8D5',
          lineWidth: (d: any) => {
            const w = Number(d?.weight) || 1;
            return Math.max(0.5, Math.min(4, w * 1.5));
          },
          endArrow: true,
          endArrowSize: 6,
          lineDash: 0,
          opacity: 0.6,
        },
        state: {
          active: {
            stroke: '#5B8FF9',
            lineWidth: 2.5,
            opacity: 1,
          },
          inactive: {
            opacity: 0.15,
          },
        },
      },
    });

    graphRef.current = graph;

    graph.on('node:click', (e: any) => {
      try {
        const nodeData = graph.getNodeData(e.target?.id);
        if (onNodeClick && nodeData) onNodeClick(nodeData);
      } catch (_) { /* ignore */ }
    });

    graph.on('edge:click', (e: any) => {
      try {
        const edgeData = graph.getEdgeData(e.target?.id);
        if (onEdgeClick && edgeData) onEdgeClick(edgeData);
      } catch (_) { /* ignore */ }
    });

    graph.setData(filteredData);
    graph.render().catch((err: any) => {
      console.error('[ForceGraph] render error:', err);
    });
  }, [filteredData, entityColorMap]);

  useEffect(() => {
    if (!isEmpty(data)) {
      render();
    }
  }, [data, render]);

  useEffect(() => {
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={styles.forceContainer}
      style={{
        width: '100%',
        height: 'calc(100vh - 160px)',
        minHeight: 400,
        display: show ? 'block' : 'none',
      }}
    />
  );
});

export default ForceGraph;
