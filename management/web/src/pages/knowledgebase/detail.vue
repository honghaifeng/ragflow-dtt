<script lang="ts" setup>
import type { SequentialBatchTaskProgress } from "@@/apis/kbs/document"
import { getDocumentListApi, getSequentialBatchParseProgressApi } from "@@/apis/kbs/document"
import { getKbDetailApi, getKnowledgeBaseEmbeddingConfigApi } from "@@/apis/kbs/knowledgebase"
import { usePagination } from "@@/composables/usePagination"
import { ArrowLeft, Refresh, Tickets } from "@element-plus/icons-vue"

defineOptions({
  name: "KnowledgeBaseDetailPage"
})

interface KnowledgeBaseDetailData {
  id: string
  name: string
  description: string
  create_date?: string
  update_date?: string
  doc_num?: number
  avatar?: string
  permission?: string
  language?: string
  nickname?: string
  embd_id?: string
  chunk_num?: number
  token_num?: number
}

interface KnowledgeBaseDocument {
  id: string
  name: string
  type?: string
  progress?: number
  progress_msg?: string
  status?: string
  run?: string
  create_date?: string
}

const route = useRoute()
const router = useRouter()
const activeTab = ref("overview")
const overviewLoading = ref(false)
const documentLoading = ref(false)
const embeddingLoading = ref(false)
const batchTask = ref<SequentialBatchTaskProgress>({
  status: "not_found",
  total: 0,
  current: 0,
  message: "暂无批量解析任务记录。"
})
const embeddingConfig = ref<Record<string, any> | null>(null)
const documents = ref<KnowledgeBaseDocument[]>([])
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

const knowledgeBase = reactive<KnowledgeBaseDetailData>({
  id: "",
  name: "",
  description: "暂无描述",
  create_date: "",
  update_date: "",
  doc_num: 0,
  avatar: "",
  permission: "",
  language: "",
  nickname: "",
  embd_id: "",
  chunk_num: 0,
  token_num: 0
})

const knowledgeBaseId = computed(() => String(route.params.id || ""))

const overviewCards = computed(() => [
  { label: "文档数量", value: knowledgeBase.doc_num || 0 },
  { label: "Chunk 数量", value: knowledgeBase.chunk_num || 0 },
  { label: "Token 数量", value: knowledgeBase.token_num || 0 },
  { label: "批量任务", value: getTaskStatusLabel(batchTask.value.status) }
])

function readStringQuery(name: string) {
  const value = route.query[name]
  return typeof value === "string" ? value : ""
}

function readNumberQuery(name: string) {
  const value = Number(readStringQuery(name))
  return Number.isFinite(value) ? value : 0
}

function applyQuerySummary() {
  knowledgeBase.id = knowledgeBaseId.value
  knowledgeBase.name = readStringQuery("name") || knowledgeBase.name
  knowledgeBase.description = readStringQuery("description") || knowledgeBase.description
  knowledgeBase.permission = readStringQuery("permission") || knowledgeBase.permission
  knowledgeBase.language = readStringQuery("language") || knowledgeBase.language
  knowledgeBase.nickname = readStringQuery("nickname") || knowledgeBase.nickname
  knowledgeBase.embd_id = readStringQuery("embd_id") || knowledgeBase.embd_id
  knowledgeBase.doc_num = readNumberQuery("doc_num") || knowledgeBase.doc_num
  knowledgeBase.chunk_num = readNumberQuery("chunk_num") || knowledgeBase.chunk_num
  knowledgeBase.token_num = readNumberQuery("token_num") || knowledgeBase.token_num
}

function getTaskStatusLabel(status: SequentialBatchTaskProgress["status"]) {
  const map: Record<SequentialBatchTaskProgress["status"], string> = {
    starting: "准备中",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
    not_found: "未建任务",
    cancelling: "取消中",
    cancelled: "已取消"
  }
  return map[status] || status
}

function getTaskStatusType(status: SequentialBatchTaskProgress["status"]) {
  const map: Record<SequentialBatchTaskProgress["status"], "info" | "success" | "warning" | "danger" | undefined> = {
    starting: "warning",
    running: "warning",
    completed: "success",
    failed: "danger",
    not_found: undefined,
    cancelling: "info",
    cancelled: "info"
  }
  return map[status]
}

function formatDocumentProgress(value?: number) {
  const progress = Number(value || 0)
  if (progress <= 0) return "未解析"
  if (progress >= 1) return "已完成"
  return `解析中 ${Math.round(progress * 100)}%`
}

function openTaskCenter() {
  router.push("/tasks/index")
}

function goBack() {
  router.push("/knowledgebase/index")
}

async function loadOverview() {
  if (!knowledgeBaseId.value) return
  overviewLoading.value = true
  try {
    const [detailResponse, taskResponse] = await Promise.all([
      getKbDetailApi(knowledgeBaseId.value) as Promise<{ data?: Partial<KnowledgeBaseDetailData> }>,
      getSequentialBatchParseProgressApi(knowledgeBaseId.value) as Promise<{ data?: SequentialBatchTaskProgress }>
    ])

    if (detailResponse?.data) {
      Object.assign(knowledgeBase, {
        ...knowledgeBase,
        ...detailResponse.data,
        id: knowledgeBaseId.value,
        description: detailResponse.data.description || knowledgeBase.description || "暂无描述"
      })
    }

    if (taskResponse?.data) {
      batchTask.value = {
        ...taskResponse.data,
        status: taskResponse.data.status || "not_found",
        total: taskResponse.data.total || 0,
        current: taskResponse.data.current || 0,
        message: taskResponse.data.message || "暂无批量解析任务记录。"
      }
    }
  } finally {
    overviewLoading.value = false
  }
}

async function loadDocuments() {
  if (!knowledgeBaseId.value) return
  documentLoading.value = true
  try {
    const response = await getDocumentListApi({
      kb_id: knowledgeBaseId.value,
      currentPage: paginationData.currentPage,
      size: paginationData.pageSize,
      sort_by: "create_date",
      sort_order: "desc"
    }) as { data?: { list?: KnowledgeBaseDocument[]; total?: number } }

    documents.value = response?.data?.list || []
    paginationData.total = response?.data?.total || 0
  } finally {
    documentLoading.value = false
  }
}

async function loadEmbeddingConfig() {
  if (!knowledgeBaseId.value) return
  embeddingLoading.value = true
  try {
    const response = await getKnowledgeBaseEmbeddingConfigApi({ kb_id: knowledgeBaseId.value }) as { data?: Record<string, any> }
    embeddingConfig.value = response?.data || null
  } finally {
    embeddingLoading.value = false
  }
}

async function refreshPage() {
  await Promise.all([loadOverview(), loadDocuments(), loadEmbeddingConfig()])
}

watch(
  [() => paginationData.currentPage, () => paginationData.pageSize],
  () => {
    loadDocuments()
  }
)

watch(
  () => route.params.id,
  () => {
    applyQuerySummary()
    paginationData.currentPage = 1
    refreshPage()
  }
)

onMounted(() => {
  applyQuerySummary()
  refreshPage()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="detail-card">
      <template #header>
        <div class="header-wrapper">
          <div class="header-main">
            <el-button text :icon="ArrowLeft" @click="goBack">
              返回列表
            </el-button>
            <div class="title-block">
              <div class="page-title">{{ knowledgeBase.name || "知识库详情" }}</div>
              <div class="page-subtitle">
                {{ knowledgeBase.description || "暂无描述" }}
              </div>
            </div>
          </div>
          <div class="header-actions">
            <el-button :icon="Tickets" @click="openTaskCenter">
              查看任务
            </el-button>
            <el-button type="primary" :icon="Refresh" @click="refreshPage">
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div v-loading="overviewLoading" class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">知识库 ID</div>
          <div class="meta-value">{{ knowledgeBase.id }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">创建人</div>
          <div class="meta-value">{{ knowledgeBase.nickname || "-" }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">语言</div>
          <div class="meta-value">{{ knowledgeBase.language || "-" }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">权限</div>
          <div class="meta-value">{{ knowledgeBase.permission || "-" }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">嵌入模型</div>
          <div class="meta-value">{{ knowledgeBase.embd_id || "-" }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">创建时间</div>
          <div class="meta-value">{{ knowledgeBase.create_date || "-" }}</div>
        </div>
      </div>

      <div class="overview-grid">
        <el-card
          v-for="card in overviewCards"
          :key="card.label"
          shadow="hover"
          class="overview-item"
        >
          <div class="overview-label">{{ card.label }}</div>
          <div class="overview-value">{{ card.value }}</div>
        </el-card>
      </div>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="概览" name="overview">
          <el-row :gutter="16">
            <el-col :lg="12" :span="24">
              <el-card shadow="hover" class="tab-card">
                <template #header>批量任务状态</template>
                <div class="status-block">
                  <el-tag :type="getTaskStatusType(batchTask.status)">
                    {{ getTaskStatusLabel(batchTask.status) }}
                  </el-tag>
                  <div class="status-text">{{ batchTask.message }}</div>
                  <div class="status-progress">
                    {{ batchTask.current || 0 }} / {{ batchTask.total || 0 }}
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :lg="12" :span="24">
              <el-card shadow="hover" class="tab-card">
                <template #header>运营建议</template>
                <ul class="simple-list">
                  <li>优先处理批量解析失败或长期未处理的文档。</li>
                  <li>嵌入模型与解析配置建议在知识库生命周期内保持稳定。</li>
                  <li>图谱、评测与权限能力将在详情页中逐步沉淀，不再继续堆叠到列表页。</li>
                </ul>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="文档" name="documents">
          <el-table v-loading="documentLoading" :data="documents">
            <el-table-column prop="name" label="文档名称" min-width="220" />
            <el-table-column prop="type" label="类型" width="120" align="center" />
            <el-table-column label="解析状态" width="140" align="center">
              <template #default="{ row }">
                <el-tag :type="(row.progress || 0) >= 1 ? 'success' : (row.progress || 0) > 0 ? 'warning' : undefined">
                  {{ formatDocumentProgress(row.progress) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress_msg" label="最新消息" min-width="260" show-overflow-tooltip />
            <el-table-column prop="create_date" label="创建时间" width="180" align="center" />
          </el-table>

          <div class="pager-wrapper">
            <el-pagination
              background
              :layout="paginationData.layout"
              :page-sizes="paginationData.pageSizes"
              :total="paginationData.total"
              :page-size="paginationData.pageSize"
              :current-page="paginationData.currentPage"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="解析配置" name="parser">
          <el-empty description="V1 先保留现有列表页配置入口，后续会把解析配置完整下沉到知识库详情页。" />
        </el-tab-pane>

        <el-tab-pane label="Embedding 配置" name="embedding">
          <div v-loading="embeddingLoading">
            <el-descriptions v-if="embeddingConfig" :column="1" border>
              <el-descriptions-item
                v-for="(value, key) in embeddingConfig"
                :key="key"
                :label="String(key)"
              >
                {{ typeof value === "object" ? JSON.stringify(value) : value || "-" }}
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="未查询到知识库 Embedding 配置" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="图谱" name="graph">
          <el-empty description="管理后台图谱聚合入口将在后续版本接入。" />
        </el-tab-pane>

        <el-tab-pane label="权限" name="permission">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前权限模式">
              {{ knowledgeBase.permission || "-" }}
            </el-descriptions-item>
            <el-descriptions-item label="创建人">
              {{ knowledgeBase.nickname || "-" }}
            </el-descriptions-item>
            <el-descriptions-item label="说明">
              V1 先保留现有权限模型展示，后续会补齐组织级共享、成员级授权与审计记录。
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="评测" name="evaluation">
          <el-empty description="评测结果将与“对话与评测”页面联动展示，V1 先保留入口位。" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.detail-card {
  border-radius: 12px;
}

.header-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.title-block {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.page-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.meta-item {
  padding: 14px 16px;
  background: var(--el-fill-color-light);
  border-radius: 10px;
}

.meta-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-value {
  margin-top: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.overview-item {
  border-radius: 10px;
}

.overview-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.overview-value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.detail-tabs {
  margin-top: 4px;
}

.tab-card {
  border-radius: 10px;
}

.status-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-text,
.status-progress {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.7;
}

.simple-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);

  li + li {
    margin-top: 10px;
  }
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
