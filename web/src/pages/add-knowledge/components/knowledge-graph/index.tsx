import { useFetchKnowledgeGraph } from '@/hooks/knowledge-hooks';
import {
  Button,
  Drawer,
  Descriptions,
  Select,
  Space,
  Tag,
  Tooltip,
  Empty,
} from 'antd';
import {
  CloseOutlined,
  ExpandOutlined,
  CompressOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import React, { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ForceGraph from './force-graph';
import styles from './index.less';

// Community color palette
const COMMUNITY_COLORS = [
  '#1890ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1',
  '#13c2c2', '#faad14', '#2f54eb', '#a0d911', '#f5222d',
  '#9254de', '#36cfc9', '#ff7a45', '#597ef7', '#ffc53d',
];

const KnowledgeGraphModal: React.FC = () => {
  const { data } = useFetchKnowledgeGraph();
  const { t } = useTranslation();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [filterEntityTypes, setFilterEntityTypes] = useState<string[]>([]);
  const [filterCommunities, setFilterCommunities] = useState<string[]>([]);
  const [highlightCommunity, setHighlightCommunity] = useState<string | null>(null);

  // Extract all entity types from graph data
  const entityTypes = useMemo(() => {
    if (!data?.graph?.nodes) return [];
    const types = new Set<string>();
    data.graph.nodes.forEach((n: any) => {
      if (n.entity_type) {
        types.add((n.entity_type || '').replace(/"/g, ''));
      }
    });
    return Array.from(types);
  }, [data]);

  // Extract all communities
  const communities = useMemo(() => {
    if (!data?.graph?.nodes) return [];
    const comms = new Set<string>();
    data.graph.nodes.forEach((n: any) => {
      if (n.communities && Array.isArray(n.communities)) {
        n.communities.forEach((c: string) => comms.add(c));
      }
    });
    return Array.from(comms);
  }, [data]);

  // Get related edges for selected node
  const relatedEdges = useMemo(() => {
    if (!selectedNode || !data?.graph?.edges) return [];
    return data.graph.edges.filter(
      (e: any) => e.source === selectedNode.id || e.target === selectedNode.id,
    );
  }, [selectedNode, data]);

  // Stats
  const nodeCount = data?.graph?.nodes?.length || 0;
  const edgeCount = data?.graph?.edges?.length || 0;

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    setSelectedEdge(null);
  }, []);

  const handleEdgeClick = useCallback((edge: any) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  }, []);

  const handleCommunityClick = useCallback(
    (community: string) => {
      setHighlightCommunity((prev) =>
        prev === community ? null : community,
      );
    },
    [],
  );

  const closeDetail = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const renderFilterBar = () => (
    <div className={styles.filterBar}>
      <FilterOutlined style={{ color: '#8c8c8c' }} />
      <Select
        mode="multiple"
        allowClear
        placeholder="实体类型筛选"
        style={{ minWidth: 180 }}
        value={filterEntityTypes}
        onChange={setFilterEntityTypes}
        options={entityTypes.map((t) => ({ label: t, value: t }))}
        maxTagCount={2}
        size="small"
      />
      {communities.length > 0 && (
        <Space size={4} wrap>
          {communities.slice(0, 10).map((c, i) => (
            <div
              key={c}
              className={`${styles.communityLegend} ${
                highlightCommunity === c ? styles.communityLegendActive : ''
              }`}
              onClick={() => handleCommunityClick(c)}
            >
              <span
                className={styles.communityDot}
                style={{
                  backgroundColor:
                    COMMUNITY_COLORS[i % COMMUNITY_COLORS.length],
                }}
              />
              {c.length > 12 ? c.slice(0, 12) + '...' : c}
            </div>
          ))}
        </Space>
      )}
      <div className={styles.toolbar}>
        <Tooltip title={isFullscreen ? '退出全屏' : '全屏'}>
          <Button
            type="text"
            icon={isFullscreen ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={() => setIsFullscreen(!isFullscreen)}
          />
        </Tooltip>
      </div>
    </div>
  );

  const renderStatsBar = () => (
    <div className={styles.statsBar}>
      <span>节点: {nodeCount}</span>
      <span>关系: {edgeCount}</span>
      <span>实体类型: {entityTypes.length}</span>
      <span>社区: {communities.length}</span>
      {filterEntityTypes.length > 0 && (
        <span style={{ color: '#1890ff' }}>
          (已筛选 {filterEntityTypes.length} 种类型)
        </span>
      )}
    </div>
  );

  const renderDetailPanel = () => {
    if (!selectedNode && !selectedEdge) return null;

    return (
      <div className={styles.detailPanel}>
        <div className={styles.detailHeader}>
          <span className={styles.detailTitle}>
            {selectedNode
              ? (selectedNode.id || '').replace(/"/g, '')
              : '关系详情'}
          </span>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={closeDetail}
          />
        </div>

        {selectedNode && (
          <>
            <div className={styles.detailSection}>
              <div className={styles.detailLabel}>实体类型</div>
              <div className={styles.detailValue}>
                <Tag color="blue">
                  {(selectedNode.entity_type || '未知').replace(/"/g, '')}
                </Tag>
              </div>
            </div>

            {selectedNode.description && (
              <div className={styles.detailSection}>
                <div className={styles.detailLabel}>描述</div>
                <div className={styles.detailValue}>
                  {(selectedNode.description || '').replace(/"/g, '')}
                </div>
              </div>
            )}

            {selectedNode.pagerank !== undefined && (
              <div className={styles.detailSection}>
                <div className={styles.detailLabel}>PageRank</div>
                <div className={styles.detailValue}>
                  {Number(selectedNode.pagerank).toFixed(4)}
                </div>
              </div>
            )}

            {selectedNode.communities &&
              selectedNode.communities.length > 0 && (
                <div className={styles.detailSection}>
                  <div className={styles.detailLabel}>所属社区</div>
                  <div className={styles.detailValue}>
                    <Space wrap>
                      {selectedNode.communities.map((c: string, i: number) => (
                        <Tag
                          key={i}
                          color="green"
                          style={{ cursor: 'pointer' }}
                          onClick={() => handleCommunityClick(c)}
                        >
                          {c}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                </div>
              )}

            {relatedEdges.length > 0 && (
              <div className={styles.detailSection}>
                <div className={styles.detailLabel}>
                  关联关系 ({relatedEdges.length})
                </div>
                {relatedEdges.map((e: any, i: number) => (
                  <div key={i} className={styles.relationItem}>
                    <span className={styles.relationSource}>
                      {(e.source || '').replace(/"/g, '')}
                    </span>
                    <span className={styles.relationArrow}>→</span>
                    <span className={styles.relationTarget}>
                      {(e.target || '').replace(/"/g, '')}
                    </span>
                    {e.description && (
                      <div
                        style={{
                          fontSize: 12,
                          color: '#8c8c8c',
                          marginTop: 4,
                        }}
                      >
                        {(e.description || '').replace(/"/g, '')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {selectedEdge && (
          <>
            <div className={styles.detailSection}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="源节点">
                  <Tag color="blue">
                    {(selectedEdge.source || '').replace(/"/g, '')}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="目标节点">
                  <Tag color="green">
                    {(selectedEdge.target || '').replace(/"/g, '')}
                  </Tag>
                </Descriptions.Item>
                {selectedEdge.weight && (
                  <Descriptions.Item label="权重">
                    {selectedEdge.weight}
                  </Descriptions.Item>
                )}
              </Descriptions>
            </div>
            {selectedEdge.description && (
              <div className={styles.detailSection}>
                <div className={styles.detailLabel}>描述</div>
                <div className={styles.detailValue}>
                  {(selectedEdge.description || '').replace(/"/g, '')}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  const graphContent = (
    <div
      className={`${styles.graphWrapper} ${
        isFullscreen ? styles.fullscreenContainer : ''
      }`}
      style={!isFullscreen ? { height: '100%' } : {}}
    >
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {renderFilterBar()}
        {renderStatsBar()}
        <div className={styles.graphMain}>
          <ForceGraph
            data={data?.graph}
            show
            filterEntityTypes={
              filterEntityTypes.length > 0 ? filterEntityTypes : undefined
            }
            filterCommunities={
              filterCommunities.length > 0 ? filterCommunities : undefined
            }
            highlightCommunity={highlightCommunity}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
          />
        </div>
      </div>
      {renderDetailPanel()}
    </div>
  );

  if (!data?.graph?.nodes?.length) {
    return (
      <section className="w-full h-full flex items-center justify-center">
        <Empty description="暂无图谱数据，请先使用 Knowledge Graph 解析方式解析文档" />
      </section>
    );
  }

  return (
    <section className="w-full h-full" style={{ minHeight: 500 }}>
      {graphContent}
    </section>
  );
};

export default KnowledgeGraphModal;
