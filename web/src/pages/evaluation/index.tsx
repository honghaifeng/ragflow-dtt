import {
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Popconfirm,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  BarChartOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import request from '@/utils/request';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const api_host = '/v1';

// Helper: unwrap getResponse:true format
const unwrap = async (p: Promise<any>) => {
  const res = await p;
  return res?.data ?? res;
};

// API functions
const evalApi = {
  listDatasets: () => unwrap(request.get(`${api_host}/evaluation/dataset`)),
  createDataset: (data: any) =>
    unwrap(request.post(`${api_host}/evaluation/dataset`, { data })),
  deleteDataset: (id: string) =>
    unwrap(request.delete(`${api_host}/evaluation/dataset/${id}`)),
  listQA: (dsId: string, page = 1, pageSize = 20) =>
    unwrap(request.get(`${api_host}/evaluation/dataset/${dsId}/qa`, {
      params: { page, page_size: pageSize },
    })),
  addQA: (dsId: string, data: any) =>
    unwrap(request.post(`${api_host}/evaluation/dataset/${dsId}/qa`, { data })),
  updateQA: (dsId: string, qaId: string, data: any) =>
    unwrap(request.put(`${api_host}/evaluation/dataset/${dsId}/qa/${qaId}`, { data })),
  deleteQA: (dsId: string, qaId: string) =>
    unwrap(request.delete(`${api_host}/evaluation/dataset/${dsId}/qa/${qaId}`)),
  runEval: (dsId: string) =>
    unwrap(request.post(`${api_host}/evaluation/dataset/${dsId}/run`)),
  getReport: (dsId: string) =>
    unwrap(request.get(`${api_host}/evaluation/dataset/${dsId}/report`)),
};

const scoreColor = (score: number) => {
  if (score >= 0.8) return '#52c41a';
  if (score >= 0.6) return '#1890ff';
  if (score >= 0.4) return '#faad14';
  return '#f5222d';
};

const EvaluationPage = () => {
  const { t } = useTranslation();

  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDs, setSelectedDs] = useState<any>(null);
  const [qaList, setQaList] = useState<any[]>([]);
  const [qaTotal, setQaTotal] = useState(0);
  const [qaPage, setQaPage] = useState(1);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [createModal, setCreateModal] = useState(false);
  const [addQaModal, setAddQaModal] = useState(false);
  const [activeTab, setActiveTab] = useState('qa');

  const [form] = Form.useForm();
  const [qaForm] = Form.useForm();

  const loadDatasets = useCallback(async () => {
    try {
      const res = await evalApi.listDatasets();
      if (res?.data) setDatasets(res.data);
    } catch (e) {
      /* ignore */
    }
  }, []);

  const loadQA = useCallback(
    async (dsId: string, page = 1) => {
      setLoading(true);
      try {
        const res = await evalApi.listQA(dsId, page);
        if (res?.data) {
          setQaList(res.data.items || []);
          setQaTotal(res.data.total || 0);
        }
      } catch (e) {
        /* ignore */
      }
      setLoading(false);
    },
    [],
  );

  const loadReport = useCallback(async (dsId: string) => {
    try {
      const res = await evalApi.getReport(dsId);
      if (res?.data) setReport(res.data);
    } catch (e) {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  useEffect(() => {
    if (selectedDs) {
      loadQA(selectedDs.id, 1);
      loadReport(selectedDs.id);
    }
  }, [selectedDs, loadQA, loadReport]);

  const handleCreateDataset = async () => {
    const values = await form.validateFields();
    const res = await evalApi.createDataset(values);
    if (res?.data) {
      message.success('创建成功');
      setCreateModal(false);
      form.resetFields();
      loadDatasets();
    }
  };

  const handleDeleteDataset = async (id: string) => {
    await evalApi.deleteDataset(id);
    message.success('已删除');
    if (selectedDs?.id === id) setSelectedDs(null);
    loadDatasets();
  };

  const handleAddQA = async () => {
    const values = await qaForm.validateFields();
    const res = await evalApi.addQA(selectedDs.id, {
      items: [
        {
          question: values.question,
          expected_answer: values.expected_answer,
        },
      ],
    });
    if (res?.data) {
      message.success(`已添加 ${res.data.count} 条`);
      setAddQaModal(false);
      qaForm.resetFields();
      loadQA(selectedDs.id, qaPage);
    }
  };

  const handleRunEval = async () => {
    if (!selectedDs?.dialog_id) {
      message.error('请先关联对话助手（dialog_id）');
      return;
    }
    setRunLoading(true);
    try {
      const res = await evalApi.runEval(selectedDs.id);
      if (res?.data) {
        message.success(
          `评测完成：准确率 ${(res.data.accuracy * 100).toFixed(1)}%`,
        );
        loadQA(selectedDs.id, qaPage);
        loadReport(selectedDs.id);
      } else {
        message.error(res?.message || '评测失败');
      }
    } catch (e: any) {
      message.error(e?.message || '评测异常');
    }
    setRunLoading(false);
  };

  const qaColumns = [
    {
      title: '问题',
      dataIndex: 'question',
      width: '25%',
      ellipsis: true,
    },
    {
      title: '标准答案',
      dataIndex: 'expected_answer',
      width: '25%',
      ellipsis: true,
    },
    {
      title: '系统回答',
      dataIndex: 'actual_answer',
      width: '25%',
      ellipsis: true,
      render: (v: string) => v || <Text type="secondary">待评测</Text>,
    },
    {
      title: '评分',
      dataIndex: 'score',
      width: 80,
      render: (v: number) =>
        v != null ? (
          <Tag color={scoreColor(v)}>{(v * 100).toFixed(1)}%</Tag>
        ) : (
          '-'
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (v: string) => {
        const map: Record<string, { color: string; text: string }> = {
          pending: { color: 'default', text: '待评测' },
          running: { color: 'processing', text: '评测中' },
          done: { color: 'success', text: '完成' },
          failed: { color: 'error', text: '失败' },
        };
        const item = map[v] || map.pending;
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '操作',
      width: 80,
      render: (_: any, record: any) => (
        <Popconfirm
          title="确认删除？"
          onConfirm={() => {
            evalApi.deleteQA(selectedDs.id, record.id).then(() => {
              loadQA(selectedDs.id, qaPage);
            });
          }}
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const renderReport = () => {
    if (!report) return <Empty description="暂无评测数据" />;
    const { summary, dimensions, distribution } = report;

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={4}>
            <Card>
              <Statistic title="总问答数" value={summary.total} />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="已完成"
                value={summary.done}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="平均分"
                value={(summary.avg_score * 100).toFixed(1)}
                suffix="%"
                valueStyle={{ color: scoreColor(summary.avg_score) }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="准确率"
                value={(summary.accuracy * 100).toFixed(1)}
                suffix="%"
                valueStyle={{ color: scoreColor(summary.accuracy) }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="失败"
                value={summary.failed}
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic title="待评测" value={summary.pending} />
            </Card>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Card title="评分维度">
              <div style={{ marginBottom: 12 }}>
                <Text>BLEU</Text>
                <Progress
                  percent={Number((dimensions.bleu * 100).toFixed(1))}
                  strokeColor="#1890ff"
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>ROUGE-L</Text>
                <Progress
                  percent={Number((dimensions.rouge_l * 100).toFixed(1))}
                  strokeColor="#52c41a"
                />
              </div>
              <div>
                <Text>关键词覆盖率</Text>
                <Progress
                  percent={Number(
                    (dimensions.keyword_coverage * 100).toFixed(1),
                  )}
                  strokeColor="#faad14"
                />
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card title="分数分布">
              {Object.entries(distribution).map(([range, count]) => (
                <div
                  key={range}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <Text style={{ width: 60 }}>{range}</Text>
                  <Progress
                    percent={
                      summary.done > 0
                        ? Number(
                            (((count as number) / summary.done) * 100).toFixed(
                              0,
                            ),
                          )
                        : 0
                    }
                    format={() => `${count}`}
                    style={{ flex: 1 }}
                  />
                </div>
              ))}
            </Card>
          </Col>
        </Row>

        {report.runs?.length > 0 && (
          <Card title="评测运行历史">
            <Table
              dataSource={report.runs}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: '时间', dataIndex: 'create_time', render: (v: number) => new Date(v).toLocaleString() },
                { title: '总数', dataIndex: 'total' },
                { title: '完成', dataIndex: 'completed' },
                { title: '平均分', dataIndex: 'avg_score', render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
                { title: '准确率', dataIndex: 'accuracy', render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
                { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'done' ? 'success' : 'processing'}>{v}</Tag> },
              ]}
            />
          </Card>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16}>
        {/* 左侧数据集列表 */}
        <Col span={6}>
          <Card
            title="评测数据集"
            extra={
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setCreateModal(true)}
              >
                新建
              </Button>
            }
          >
            <List
              dataSource={datasets}
              renderItem={(item: any) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background:
                      selectedDs?.id === item.id ? '#e6f7ff' : 'transparent',
                    padding: '8px 12px',
                    borderRadius: 6,
                  }}
                  onClick={() => setSelectedDs(item)}
                  actions={[
                    <Popconfirm
                      key="del"
                      title="确认删除？"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        handleDeleteDataset(item.id);
                      }}
                    >
                      <DeleteOutlined
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: '#ff4d4f' }}
                      />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={item.name}
                    description={`${item.qa_count || 0} 条问答`}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无数据集' }}
            />
          </Card>
        </Col>

        {/* 右侧详情 */}
        <Col span={18}>
          {selectedDs ? (
            <Card
              title={selectedDs.name}
              extra={
                <Space>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={runLoading}
                    onClick={handleRunEval}
                  >
                    运行评测
                  </Button>
                  <Button
                    icon={<PlusOutlined />}
                    onClick={() => setAddQaModal(true)}
                  >
                    添加问答
                  </Button>
                </Space>
              }
            >
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                  {
                    key: 'qa',
                    label: '问答对',
                    children: (
                      <Table
                        dataSource={qaList}
                        columns={qaColumns}
                        rowKey="id"
                        loading={loading}
                        size="small"
                        pagination={{
                          total: qaTotal,
                          current: qaPage,
                          pageSize: 20,
                          onChange: (p) => {
                            setQaPage(p);
                            loadQA(selectedDs.id, p);
                          },
                        }}
                      />
                    ),
                  },
                  {
                    key: 'report',
                    label: (
                      <span>
                        <BarChartOutlined /> 评测报表
                      </span>
                    ),
                    children: renderReport(),
                  },
                ]}
              />
            </Card>
          ) : (
            <Card>
              <Empty description="请选择或创建一个评测数据集" />
            </Card>
          )}
        </Col>
      </Row>

      {/* 创建数据集Modal */}
      <Modal
        title="新建评测数据集"
        open={createModal}
        onOk={handleCreateDataset}
        onCancel={() => setCreateModal(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="评测数据集名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
          <Form.Item name="dialog_id" label="关联对话助手ID">
            <Input placeholder="对话助手的ID（用于运行评测）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加QA Modal */}
      <Modal
        title="添加问答对"
        open={addQaModal}
        onOk={handleAddQA}
        onCancel={() => setAddQaModal(false)}
        width={640}
      >
        <Form form={qaForm} layout="vertical">
          <Form.Item
            name="question"
            label="问题"
            rules={[{ required: true }]}
          >
            <TextArea rows={2} placeholder="输入测试问题" />
          </Form.Item>
          <Form.Item
            name="expected_answer"
            label="标准答案"
            rules={[{ required: true }]}
          >
            <TextArea rows={4} placeholder="输入期望的标准答案" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default EvaluationPage;
