import {
  Button,
  Card,
  Empty,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CopyOutlined,
  DeleteOutlined,
  LinkOutlined,
  PlusOutlined,
  TeamOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { useCallback, useEffect, useMemo, useState } from 'react';
import request from '@/utils/request';
import styles from './index.less';

const { Text } = Typography;

// Helper: @/utils/request uses getResponse:true, so response is { data: body, response }
const api = async (url: string, options?: any) => {
  const res = await request(url, options);
  return res?.data ?? res;
};

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  owner: { label: '拥有者', color: 'gold' },
  admin: { label: '管理员', color: 'blue' },
  editor: { label: '编辑者', color: 'green' },
  viewer: { label: '只读', color: 'default' },
};

const OrganizationPage = () => {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [inviteLink, setInviteLink] = useState('');
  const [createForm] = Form.useForm();
  const [addMemberForm] = Form.useForm();
  const [settingForm] = Form.useForm();

  const fetchOrgs = useCallback(async () => {
    try {
      const res = await api('/v1/org/list', { method: 'GET' });
      if (res.code === 0) {
        setOrgs(res.data || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchMembers = useCallback(async (orgId: string) => {
    setLoading(true);
    try {
      const res = await api(`/v1/org/${orgId}/members`, { method: 'GET' });
      if (res.code === 0) {
        setMembers(res.data || []);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  useEffect(() => {
    if (selectedOrg) {
      fetchMembers(selectedOrg.id);
      settingForm.setFieldsValue({
        name: selectedOrg.name,
        description: selectedOrg.description,
      });
      setInviteLink('');
    }
  }, [selectedOrg, fetchMembers, settingForm]);

  const myRole = useMemo(() => selectedOrg?.role || 'viewer', [selectedOrg]);
  const canManage = myRole === 'owner' || myRole === 'admin';

  const handleCreateOrg = async () => {
    try {
      const values = await createForm.validateFields();
      const res = await api('/v1/org/create', {
        method: 'POST',
        data: values,
      });
      if (res.code === 0) {
        message.success('创建成功');
        setCreateModalOpen(false);
        createForm.resetFields();
        fetchOrgs();
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteOrg = async () => {
    if (!selectedOrg) return;
    try {
      const res = await api(`/v1/org/${selectedOrg.id}/delete`, {
        method: 'DELETE',
      });
      if (res.code === 0) {
        message.success('已删除');
        setSelectedOrg(null);
        fetchOrgs();
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddMember = async () => {
    try {
      const values = await addMemberForm.validateFields();
      const res = await api(`/v1/org/${selectedOrg.id}/member/add`, {
        method: 'POST',
        data: { email: values.email, role: values.role || 'viewer' },
      });
      if (res.code === 0) {
        const d = res.data;
        if (d.added?.length > 0) message.success(`已添加 ${d.added.length} 人`);
        if (d.not_found?.length > 0)
          message.warning(`未找到: ${d.not_found.join(', ')}`);
        setAddMemberOpen(false);
        addMemberForm.resetFields();
        fetchMembers(selectedOrg.id);
        fetchOrgs();
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    try {
      const res = await api(
        `/v1/org/${selectedOrg.id}/member/${userId}/remove`,
        { method: 'DELETE' },
      );
      if (res.code === 0) {
        message.success('已移除');
        fetchMembers(selectedOrg.id);
        fetchOrgs();
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleChangeRole = async (userId: string, role: string) => {
    try {
      const res = await api(
        `/v1/org/${selectedOrg.id}/member/${userId}/role`,
        { method: 'PUT', data: { role } },
      );
      if (res.code === 0) {
        message.success('角色已更新');
        fetchMembers(selectedOrg.id);
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateInvite = async () => {
    try {
      const res = await api(`/v1/org/${selectedOrg.id}/invite-link`, {
        method: 'POST',
        data: { expire_hours: 72 },
      });
      if (res.code === 0) {
        const code = res.data.code;
        const link = `${window.location.origin}/organization?invite=${code}`;
        setInviteLink(link);
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateOrg = async () => {
    try {
      const values = await settingForm.validateFields();
      const res = await api(`/v1/org/${selectedOrg.id}/update`, {
        method: 'PUT',
        data: values,
      });
      if (res.code === 0) {
        message.success('已更新');
        fetchOrgs();
        setSelectedOrg({ ...selectedOrg, ...values });
      } else {
        message.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Handle invite code on page load
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const inviteCode = params.get('invite');
    if (inviteCode) {
      api(`/v1/org/join/${inviteCode}`, { method: 'POST' }).then((res) => {
        if (res.code === 0) {
          message.success(`已加入组织: ${res.data.org_name}`);
          fetchOrgs();
          window.history.replaceState({}, '', '/organization');
        } else {
          message.error(res.message);
        }
      });
    }
  }, [fetchOrgs]);

  const memberColumns = [
    {
      title: '用户',
      dataIndex: 'nickname',
      key: 'nickname',
      render: (text: string, record: any) => (
        <Space>
          <span>{text}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.email}
          </Text>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 150,
      render: (role: string, record: any) => {
        if (!canManage || role === 'owner') {
          const r = ROLE_LABELS[role] || { label: role, color: 'default' };
          return <Tag color={r.color}>{r.label}</Tag>;
        }
        return (
          <Select
            value={role}
            size="small"
            style={{ width: 100 }}
            onChange={(v) => handleChangeRole(record.user_id, v)}
          >
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="editor">编辑者</Select.Option>
            <Select.Option value="viewer">只读</Select.Option>
          </Select>
        );
      },
    },
    {
      title: '加入时间',
      dataIndex: 'create_date',
      key: 'create_date',
      width: 180,
    },
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'action',
            width: 80,
            render: (_: any, record: any) =>
              record.role !== 'owner' ? (
                <Popconfirm
                  title="确认移除？"
                  onConfirm={() => handleRemoveMember(record.user_id)}
                >
                  <Button type="link" danger size="small" icon={<DeleteOutlined />} />
                </Popconfirm>
              ) : null,
          },
        ]
      : []),
  ];

  const tabItems = [
    {
      key: 'members',
      label: '成员管理',
      children: (
        <>
          <div className={styles.memberActions}>
            <Space>
              <span>共 {members.length} 位成员</span>
            </Space>
            {canManage && (
              <Space>
                <Button
                  icon={<UserAddOutlined />}
                  onClick={() => setAddMemberOpen(true)}
                >
                  添加成员
                </Button>
                <Button icon={<LinkOutlined />} onClick={handleGenerateInvite}>
                  生成邀请链接
                </Button>
              </Space>
            )}
          </div>
          {inviteLink && (
            <div className={styles.inviteLinkBox}>
              <Text copyable={{ text: inviteLink }}>
                <LinkOutlined /> {inviteLink}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                （72小时有效）
              </Text>
            </div>
          )}
          <Table
            columns={memberColumns}
            dataSource={members}
            rowKey="user_id"
            loading={loading}
            pagination={false}
            size="small"
          />
        </>
      ),
    },
    {
      key: 'settings',
      label: '设置',
      children: canManage ? (
        <div className={styles.settingForm}>
          <Form form={settingForm} layout="vertical">
            <Form.Item name="name" label="组织名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" onClick={handleUpdateOrg}>
                  保存
                </Button>
                {myRole === 'owner' && (
                  <Popconfirm title="确认删除组织？" onConfirm={handleDeleteOrg}>
                    <Button danger>删除组织</Button>
                  </Popconfirm>
                )}
              </Space>
            </Form.Item>
          </Form>
        </div>
      ) : (
        <Text type="secondary">仅管理员可修改设置</Text>
      ),
    },
  ];

  return (
    <div className={styles.organizationPage}>
      <Card className={styles.leftPanel} size="small">
        <Button
          type="primary"
          block
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
          style={{ marginBottom: 12 }}
        >
          创建组织
        </Button>
        <div className={styles.orgList}>
          {orgs.map((org) => (
            <div
              key={org.id}
              className={`${styles.orgItem} ${
                selectedOrg?.id === org.id ? styles.orgItemActive : ''
              }`}
              onClick={() => setSelectedOrg(org)}
            >
              <div className={styles.orgName}>
                <TeamOutlined style={{ marginRight: 6 }} />
                {org.name}
              </div>
              <div className={styles.orgMeta}>
                <Tag color={ROLE_LABELS[org.role]?.color} style={{ fontSize: 11 }}>
                  {ROLE_LABELS[org.role]?.label}
                </Tag>
                {org.member_count} 成员 · {org.kb_count} 知识库
              </div>
            </div>
          ))}
          {orgs.length === 0 && (
            <Empty description="暂无组织" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      </Card>

      <Card className={styles.rightPanel} size="small">
        {selectedOrg ? (
          <>
            <h3>
              <TeamOutlined style={{ marginRight: 8 }} />
              {selectedOrg.name}
            </h3>
            <Tabs items={tabItems} />
          </>
        ) : (
          <div className={styles.emptyWrapper}>
            <Empty description="请选择或创建一个组织" />
          </div>
        )}
      </Card>

      <Modal
        title="创建组织"
        open={createModalOpen}
        onOk={handleCreateOrg}
        onCancel={() => setCreateModalOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="组织名称"
            rules={[{ required: true, message: '请输入组织名称' }]}
          >
            <Input placeholder="如：电力运维部" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="组织描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加成员"
        open={addMemberOpen}
        onOk={handleAddMember}
        onCancel={() => setAddMemberOpen(false)}
        okText="添加"
        cancelText="取消"
      >
        <Form form={addMemberForm} layout="vertical">
          <Form.Item
            name="email"
            label="用户邮箱"
            rules={[{ required: true, message: '请输入邮箱' }]}
          >
            <Input placeholder="输入已注册用户的邮箱" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="viewer">
            <Select>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="editor">编辑者</Select.Option>
              <Select.Option value="viewer">只读</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OrganizationPage;
