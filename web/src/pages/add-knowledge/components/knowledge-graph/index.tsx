import { useFetchKnowledgeGraph } from '@/hooks/knowledge-hooks';
import {
  Button,
  Descriptions,
  Input,
  Select,
  Space,
  Steps,
  Tag,
  Tooltip,
} from 'antd';
import {
  ApartmentOutlined,
  CloseOutlined,
  CompressOutlined,
  ExpandOutlined,
  FilterOutlined,
  NodeIndexOutlined,
  RocketOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import React, { useCallback, useMemo, useRef, useState } from 'react';
import ForceGraph from './force-graph';
import styles from './index.less';

const KnowledgeGraphModal: React.FC = () => {
  const { data } = useFetchKnowledgeGraph();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [filterEntityTypes, setFilterEntityTypes] = useState<string[]>([]);
  const [filterRelationTypes, setFilterRelationTypes] = useState<string[]>([]);
  const [searchValue, setSearchValue] = useState('');
  const [highlightNodeId, setHighlightNodeId] = useState<string | null>(null);
  const [showCommunityPanel, setShowCommunityPanel] = useState(false);
  const [selectedCommunityIdx, setSelectedCommunityIdx] = useState<number | null>(null);
  const graphRef = useRef<{ focusNode: (nodeId: string) => void } | null>(null);

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

  const relationTypes = useMemo(() => {
    if (!data?.graph?.edges) return [];
    const types = new Set<string>();
    data.graph.edges.forEach((e: any) => {
      const desc = (e.description || '').replace(/"/g, '').trim();
      if (desc) types.add(desc);
    });
    return Array.from(types);
  }, [data]);

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

  const closeDetail = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const handleSearch = useCallback(
    (value: string) => {
      if (!value || !data?.graph?.nodes) {
        setHighlightNodeId(null);
        return;
      }
      const found = data.graph.nodes.find((n: any) =>
        (n.id || '').toLowerCase().includes(value.toLowerCase()),
      );
      if (found) {
        setHighlightNodeId(found.id);
        graphRef.current?.focusNode(found.id);
      }
    },
    [data],
  );

  const relatedEdges = useMemo(() => {
    if (!selectedNode || !data?.graph?.edges) return [];
    return data.graph.edges.filter(
      (e: any) => e.source === selectedNode.id || e.target === selectedNode.id,
    );
  }, [selectedNode, data]);

  // Empty state
  if (!data?.graph?.nodes?.length) {
    return (
      <section className="w-full h-full flex items-center justify-center">
        <div className={styles.emptyGuide}>
          <ApartmentOutlined className={styles.emptyGuideIcon} />
          <h3 className={styles.emptyGuideTitle}>暂无图谱数据</h3>
          <p className={styles.emptyGuideDesc}>
            知识图谱需要使用 GraphRAG 解析方式处理文档后自动生成
          </p>
          <Steps
            direction="vertical"
            size="small"
            current={-1}
            className={styles.emptyGuideSteps}
            items={[
              {
                title: '选择解析方式',
                description: '在知识库配置中，将解析方式设置为 Knowledge Graph',
                icon: <SettingOutlined />,
              },
              {
                title: '上传并解析文档',
                description: '上传文档并点击解析，系统将自动提取实体和关系',
                icon: <RocketOutlined />,
              },
              {
                title: '查看知识图谱',
                description: 'GraphRAG 提取完成后，图谱将自动展示在此页面',
                icon: <NodeIndexOutlined />,
              },
            ]}
          />
        </div>
      </section>
    );
  }

  return (
    <section
      className={isFullscreen ? styles.fullscreenContainer : ''}
      style={isFullscreen ? undefined : { position: 'relative', width: '100%' }}
    >
      {/* Filter bar - overlay on top */}
      <div className={styles.filterBar}>
        <FilterOutlined style={{ color: '#8c8c8c' }} />
        <Select
          mode="multiple"
          allowClear
          placeholder="实体类型筛选"
          style={{ minWidth: 160 }}
          value={filterEntityTypes}
          onChange={setFilterEntityTypes}
          options={entityTypes.map((t) => ({ label: t, value: t }))}
          maxTagCount={2}
          size="small"
        />
        {relationTypes.length > 0 && (
          <Select
            mode="multiple"
            allowClear
            placeholder="关系类型筛选"
            style={{ minWidth: 160 }}
            value={filterRelationTypes}
            onChange={setFilterRelationTypes}
            options={relationTypes.map((t) => ({ label: t, value: t }))}
            maxTagCount={2}
            size="small"
          />
        )}
        <Input.Search
          placeholder="搜索实体"
          style={{ width: 180 }}
          size="small"
          allowClear
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onSearch={handleSearch}
          prefix={<SearchOutlined />}
        />
        <div className={styles.statsInfo}>
          <span>节点: {nodeCount}</span>
          <span>关系: {edgeCount}</span>
          <span>实体类型: {entityTypes.length}</span>
        </div>
        <div className={styles.toolbar}>
          <Tooltip title={showCommunityPanel ? '关闭社区面板' : '社区聚类'}>
            <Button
              type="text"
              icon={<TeamOutlined />}
              onClick={() => setShowCommunityPanel(!showCommunityPanel)}
              style={showCommunityPanel ? { color: '#1890ff' } : undefined}
            />
          </Tooltip>
          <Tooltip title={isFullscreen ? '退出全屏' : '全屏'}>
            <Button
              type="text"
              icon={isFullscreen ? <CompressOutlined /> : <ExpandOutlined />}
              onClick={() => setIsFullscreen(!isFullscreen)}
            />
          </Tooltip>
        </div>
      </div>

      {/* Graph - fills remaining space */}
      <ForceGraph
        ref={graphRef}
        data={data?.graph}
        show
        filterEntityTypes={filterEntityTypes.length > 0 ? filterEntityTypes : undefined}
        filterRelationTypes={filterRelationTypes.length > 0 ? filterRelationTypes : undefined}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
      />

      {/* Community panel - overlay on left */}
      {showCommunityPanel && (data?.community_reports?.length ?? 0) > 0 && (
        <div className={styles.communityPanel}>
          <div className={styles.communityHeader}>
            <span className={styles.communityTitle}>
              <TeamOutlined style={{ marginRight: 6 }} />
              社区聚类 ({data.community_reports.length})
            </span>
            <Button type="text" size="small" icon={<CloseOutlined />} onClick={() => { setShowCommunityPanel(false); setSelectedCommunityIdx(null); }} />
          </div>
          <div className={styles.communityList}>
            {data.community_reports.map((cr: any, idx: number) => (
              <div
                key={idx}
                className={`${styles.communityItem} ${selectedCommunityIdx === idx ? styles.communityItemActive : ''}`}
                onClick={() => setSelectedCommunityIdx(selectedCommunityIdx === idx ? null : idx)}
              >
                <div className={styles.communityItemTitle}>
                  {cr.title || `社区 ${idx + 1}`}
                  {cr.weight && <span className={styles.communityWeight}>权重: {Number(cr.weight).toFixed(2)}</span>}
                </div>
                {cr.entities && cr.entities.length > 0 && (
                  <div className={styles.communityEntities}>
                    {cr.entities.slice(0, 6).map((ent: string, i: number) => (
                      <Tag key={i} color="blue" style={{ fontSize: 11, marginBottom: 4 }}>{ent.replace(/"/g, '')}</Tag>
                    ))}
                    {cr.entities.length > 6 && <Tag style={{ fontSize: 11, marginBottom: 4 }}>+{cr.entities.length - 6}</Tag>}
                  </div>
                )}
                {selectedCommunityIdx === idx && cr.report && (
                  <div className={styles.communityReport}>
                    {cr.report.length > 300 ? cr.report.slice(0, 300) + '...' : cr.report}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detail panel - overlay on right */}
      {(selectedNode || selectedEdge) && (
        <div className={styles.detailPanel}>
          <div className={styles.detailHeader}>
            <span className={styles.detailTitle}>
              {selectedNode ? (selectedNode.id || '').replace(/"/g, '') : '关系详情'}
            </span>
            <Button type="text" size="small" icon={<CloseOutlined />} onClick={closeDetail} />
          </div>
          {selectedNode && (
            <>
              <div className={styles.detailSection}>
                <div className={styles.detailLabel}>实体类型</div>
                <div className={styles.detailValue}>
                  <Tag color="blue">{(selectedNode.entity_type || '未知').replace(/"/g, '')}</Tag>
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
                  <div className={styles.detailValue}>{Number(selectedNode.pagerank).toFixed(4)}</div>
                </div>
              )}
              {relatedEdges.length > 0 && (
                <div className={styles.detailSection}>
                  <div className={styles.detailLabel}>关联关系 ({relatedEdges.length})</div>
                  {relatedEdges.map((e: any, i: number) => (
                    <div key={i} className={styles.relationItem}>
                      <span className={styles.relationSource}>{(e.source || '').replace(/"/g, '')}</span>
                      <span className={styles.relationArrow}>→</span>
                      <span className={styles.relationTarget}>{(e.target || '').replace(/"/g, '')}</span>
                      {e.description && (
                        <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
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
                    <Tag color="blue">{(selectedEdge.source || '').replace(/"/g, '')}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="目标节点">
                    <Tag color="green">{(selectedEdge.target || '').replace(/"/g, '')}</Tag>
                  </Descriptions.Item>
                  {selectedEdge.weight && (
                    <Descriptions.Item label="权重">{selectedEdge.weight}</Descriptions.Item>
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
      )}
    </section>
  );
};

export default KnowledgeGraphModal;
