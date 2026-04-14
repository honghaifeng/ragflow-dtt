import { ElementDatum, Graph, IElementEvent } from '@antv/g6';
import isEmpty from 'lodash/isEmpty';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { buildNodesAndCombos } from './util';

import styles from './index.less';

const TooltipColorMap = {
  combo: 'red',
  node: 'black',
  edge: 'blue',
};

interface IProps {
  data: any;
  show: boolean;
  filterEntityTypes?: string[];
  filterCommunities?: string[];
  highlightCommunity?: string | null;
  onNodeClick?: (node: any) => void;
  onEdgeClick?: (edge: any) => void;
}

const ForceGraph = ({
  data,
  show,
  filterEntityTypes,
  filterCommunities,
  highlightCommunity,
  onNodeClick,
  onEdgeClick,
}: IProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  const filteredData = useMemo(() => {
    if (!isEmpty(data)) {
      const graphData = { ...data };

      let nodes = graphData.nodes || [];
      let edges = graphData.edges || [];

      // Filter by entity type
      if (filterEntityTypes && filterEntityTypes.length > 0) {
        nodes = nodes.filter(
          (n: any) =>
            !n.entity_type ||
            filterEntityTypes.includes(
              (n.entity_type || '').replace(/"/g, ''),
            ),
        );
        const nodeIdSet = new Set(nodes.map((n: any) => n.id));
        edges = edges.filter(
          (e: any) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target),
        );
      }

      // Filter by community
      if (filterCommunities && filterCommunities.length > 0) {
        nodes = nodes.filter((n: any) => {
          if (!n.communities || !Array.isArray(n.communities)) return true;
          return n.communities.some((c: string) =>
            filterCommunities.includes(c),
          );
        });
        const nodeIdSet = new Set(nodes.map((n: any) => n.id));
        edges = edges.filter(
          (e: any) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target),
        );
      }

      const mi = buildNodesAndCombos(nodes);
      return { edges, ...mi };
    }
    return { nodes: [], edges: [] };
  }, [data, filterEntityTypes, filterCommunities]);

  const render = useCallback(() => {
    const graph = new Graph({
      container: containerRef.current!,
      autoFit: 'view',
      autoResize: true,
      behaviors: [
        'drag-element',
        'drag-canvas',
        'zoom-canvas',
        'collapse-expand',
        {
          type: 'hover-activate',
          degree: 1,
        },
      ],
      plugins: [
        {
          type: 'tooltip',
          enterable: true,
          getContent: (e: IElementEvent, items: ElementDatum) => {
            if (Array.isArray(items)) {
              if (items.some((x) => x?.isCombo)) {
                return `<p style="font-weight:600;color:red">${items?.[0]?.data?.label}</p>`;
              }
              let result = ``;
              items.forEach((item) => {
                result += `<section style="color:${TooltipColorMap[e['targetType'] as keyof typeof TooltipColorMap]};"><h3>${item?.id}</h3>`;
                if (item?.entity_type) {
                  result += `<div style="padding-bottom: 6px;"><b>Entity type: </b>${item?.entity_type}</div>`;
                }
                if (item?.weight) {
                  result += `<div><b>Weight: </b>${item?.weight}</div>`;
                }
                if (item?.description) {
                  result += `<p>${item?.description}</p>`;
                }
              });
              return result + '</section>';
            }
            return undefined;
          },
        },
      ],
      layout: {
        type: 'combo-combined',
        preventOverlap: true,
        comboPadding: 1,
        spacing: 100,
      },
      node: {
        style: {
          size: (d: any) => {
            // Size based on pagerank
            const pagerank = d?.pagerank || 0;
            const base = 120;
            return base + pagerank * 200;
          },
          labelText: (d: any) => d.id,
          labelFontSize: 40,
          labelOffsetY: 20,
          labelPlacement: 'center',
          labelWordWrap: true,
          // Highlight community
          opacity: (d: any) => {
            if (!highlightCommunity) return 1;
            if (
              d.communities &&
              Array.isArray(d.communities) &&
              d.communities.includes(highlightCommunity)
            ) {
              return 1;
            }
            return 0.15;
          },
        },
        palette: {
          type: 'group',
          field: (d: any) => {
            return d?.entity_type as string;
          },
        },
      },
      edge: {
        style: (model: any) => {
          const weight: number = Number(model?.weight) || 2;
          const lineWeight = weight * 4;
          return {
            stroke: '#99ADD1',
            lineWidth: lineWeight > 10 ? 10 : lineWeight,
            opacity: highlightCommunity ? 0.2 : 1,
          };
        },
      },
    });

    if (graphRef.current) {
      graphRef.current.destroy();
    }

    graphRef.current = graph;

    // Node click event
    graph.on('node:click', (e: any) => {
      const nodeData = e.target?.config?.data || graph.getNodeData(e.target?.id);
      if (onNodeClick && nodeData) {
        onNodeClick(nodeData);
      }
    });

    // Edge click event
    graph.on('edge:click', (e: any) => {
      const edgeData = e.target?.config?.data || graph.getEdgeData(e.target?.id);
      if (onEdgeClick && edgeData) {
        onEdgeClick(edgeData);
      }
    });

    graph.setData(filteredData);
    graph.render();
  }, [filteredData, highlightCommunity, onNodeClick, onEdgeClick]);

  useEffect(() => {
    if (!isEmpty(data)) {
      render();
    }
  }, [data, render]);

  // Expose graph instance for external use (e.g., export)
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
        height: '100%',
        display: show ? 'block' : 'none',
      }}
    />
  );
};

export default ForceGraph;
