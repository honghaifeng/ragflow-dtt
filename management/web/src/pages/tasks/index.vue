<script lang="ts" setup>
import type { SequentialBatchTaskProgress } from "@@/apis/kbs/document"
import { getSequentialBatchParseProgressApi, startSequentialBatchParseAsyncApi } from "@@/apis/kbs/document"
import { getKnowledgeBaseListApi } from "@@/apis/kbs/knowledgebase"
import { usePagination } from "@@/composables/usePagination"
import { Refresh, VideoPlay, View } from "@element-plus/icons-vue"

defineOptions({
  name: "TaskCenter"
})

interface KnowledgeBaseRow {
  id: string
  name: string
  description?: string
  doc_num?: number
  chunk_num?: number
  token_num?: number
  nickname?: string
  create_date?: string
  embd_id?: string
  permission?: string
  language?: string
}

interface TaskRow extends KnowledgeBaseRow {
  task: SequentialBatchTaskProgress
}

type TaskStatus = SequentialBatchTaskProgress["status"]

const router = useRouter()
const loading = ref(false)
const detailDrawerVisible = ref(false)
const pollingTimer = ref<NodeJS.Timeout | null>(null)
const selectedTask = ref<TaskRow | null>(null)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination({ pageSize: 8 })

const searchData = reactive({
  keyword: "",
  status: "all"
})

const rawKnowledgeBases = ref<KnowledgeBaseRow[]>([])
const taskRows = ref<TaskRow[]>([])

const statusOptions = [
  { label: "全部状态", value: "all" },
  { label: "准备中", value: "starting" },
  { label: "运行中", value: "running" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" },
  { label: "未找到任务", value: "not_found" }
]

const filteredTaskRows = computed(() => {
  return taskRows.value.filter((row) => {
    const keywordMatched = !searchData.keyword || row.name?.toLowerCase().includes(searchData.keyword.trim().toLowerCase())
    const statusMatched = searchData.status === "all" || row.task.status === searchData.status
    return keywordMatched && statusMatched
  })
})

const summaryCards = computed(() => {
  const rows = filteredTaskRows.value
  const total = rows.length
  const running = rows.filter((item) => item.task.status === "running" || item.task.status === "starting").length
  const completed = rows.filter((item) => item.task.status === "completed").length
  const failed = rows.filter((item) => item.task.status === "failed").length
  const idle = rows.filter((item) => item.task.status === "not_found").length
  return [
    { label: "知识库总数", value: total, type: "info" },
    { label: "运行中任务", value: running, type: "warning" },
    { label: "已完成任务", value: completed, type: "success" },
    { label: "失败任务", value: failed, type: "danger" },
    { label: "未建任务", value: idle, type: "" }
  ]
})

const hasActiveTasks = computed(() => taskRows.value.some((item) => item.task.status === "running" || item.task.status === "starting"))

function normalizeTaskProgress(data?: Partial<SequentialBatchTaskProgress>): SequentialBatchTaskProgress {
  return {
    status: "not_found",
    total: 0,
    current: 0,
    message: "未找到该知识库的批量解析任务记录。",
    ...data
  }
}

function getStatusLabel(status: TaskStatus) {
  const statusMap: Record<TaskStatus, string> = {
    starting: "准备中",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
    not_found: "未建任务",
    cancelling: "取消中",
    cancelled: "已取消"
  }
  return statusMap[status] || status
}

function getStatusType(status: TaskStatus) {
  const typeMap: Record<TaskStatus, "info" | "success" | "warning" | "danger" | undefined> = {
    starting: "warning",
    running: "warning",
    completed: "success",
    failed: "danger",
    not_found: undefined,
    cancelling: "info",
    cancelled: "info"
  }
  return typeMap[status]
}

function formatProgress(row: TaskRow) {
  const { current = 0, total = 0, status } = row.task
  if (status === "not_found") return 0
  if (total <= 0) return status === "completed" ? 100 : 0
  return Math.min(100, Math.round((current / total) * 100))
}

function formatStartTime(value?: number) {
  if (!value) return "-"
  return new Date(value * 1000).toLocaleString()
}

function handleSearch() {
  if (paginationData.currentPage === 1) {
    getTableData()
  } else {
    paginationData.currentPage = 1
  }
}

function resetSearch() {
  searchData.keyword = ""
  searchData.status = "all"
  handleSearch()
}

async function loadTaskProgress(knowledgeBases: KnowledgeBaseRow[]) {
  const results = await Promise.allSettled(
    knowledgeBases.map(async (knowledgeBase) => {
      const response = await getSequentialBatchParseProgressApi(knowledgeBase.id) as { data?: SequentialBatchTaskProgress }
      return {
        ...knowledgeBase,
        task: normalizeTaskProgress(response?.data)
      } as TaskRow
    })
  )

  taskRows.value = results.map((result, index) => {
    if (result.status === "fulfilled") {
      return result.value
    }

    return {
      ...knowledgeBases[index],
      task: normalizeTaskProgress({
        status: "failed",
        message: "任务状态获取失败，请稍后重试。"
      })
    }
  })
}

async function getTableData() {
  loading.value = true
  try {
    const response = await getKnowledgeBaseListApi({
      currentPage: paginationData.currentPage,
      size: paginationData.pageSize,
      name: searchData.keyword,
      sort_by: "create_date",
      sort_order: "desc"
    }) as { data?: { list?: KnowledgeBaseRow[]; total?: number } }

    const list = response?.data?.list || []
    rawKnowledgeBases.value = list
    paginationData.total = response?.data?.total || 0
    await loadTaskProgress(list)
  } catch {
    rawKnowledgeBases.value = []
    taskRows.value = []
    paginationData.total = 0
  } finally {
    loading.value = false
  }
}

async function refreshTaskStatuses() {
  if (!rawKnowledgeBases.value.length) return
  await loadTaskProgress(rawKnowledgeBases.value)
}

async function handleStartTask(row: TaskRow) {
  try {
    await startSequentialBatchParseAsyncApi(row.id)
    ElMessage.success(`已启动知识库「${row.name}」的批量解析任务`)
    await refreshTaskStatuses()
  } catch {
    // request 拦截器已统一提示
  }
}

function handleViewDetail(row: TaskRow) {
  selectedTask.value = row
  detailDrawerVisible.value = true
}

function openKnowledgeBaseDetail(row: TaskRow) {
  router.push({
    name: "KnowledgeBaseDetail",
    params: { id: row.id },
    query: {
      name: row.name || "",
      description: row.description || "",
      doc_num: String(row.doc_num || 0),
      chunk_num: String(row.chunk_num || 0),
      token_num: String(row.token_num || 0),
      permission: row.permission || "",
      language: row.language || "",
      nickname: row.nickname || "",
      embd_id: row.embd_id || ""
    }
  })
}

function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

watch(
  [() => paginationData.currentPage, () => paginationData.pageSize],
  getTableData,
  { immediate: true }
)

watch(
  hasActiveTasks,
  (active) => {
    stopPolling()
    if (active) {
      pollingTimer.value = setInterval(() => {
        refreshTaskStatuses()
      }, 10000)
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="page-header">
          <div>
            <div class="page-title">任务中心</div>
            <div class="page-subtitle">统一查看知识库级批量解析任务状态，快速处理失败与阻塞问题。</div>
          </div>
          <el-button :icon="Refresh" @click="refreshTaskStatuses">
            刷新状态
          </el-button>
        </div>
      </template>

      <el-form inline class="filter-bar">
        <el-form-item label="知识库">
          <el-input v-model="searchData.keyword" placeholder="按知识库名称搜索" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchData.status" style="width: 180px">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            查询
          </el-button>
          <el-button @click="resetSearch">
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <div class="summary-grid">
        <el-card
          v-for="card in summaryCards"
          :key="card.label"
          shadow="hover"
          class="summary-card"
        >
          <div class="summary-label">{{ card.label }}</div>
          <div class="summary-value" :class="card.type">{{ card.value }}</div>
        </el-card>
      </div>

      <el-table v-loading="loading" :data="filteredTaskRows" class="task-table">
        <el-table-column prop="name" label="知识库" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="openKnowledgeBaseDetail(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="doc_num" label="文档数" width="90" align="center" />
        <el-table-column label="任务状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.task.status)">
              {{ getStatusLabel(row.task.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="180">
          <template #default="{ row }">
            <el-progress :percentage="formatProgress(row)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column label="当前/总计" width="110" align="center">
          <template #default="{ row }">
            {{ row.task.current || 0 }} / {{ row.task.total || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatStartTime(row.task.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="task.message" label="最新消息" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button text bg size="small" :icon="View" @click="handleViewDetail(row)">
              详情
            </el-button>
            <el-button
              text
              bg
              size="small"
              type="primary"
              :icon="VideoPlay"
              :disabled="row.task.status === 'running' || row.task.status === 'starting'"
              @click="handleStartTask(row)"
            >
              启动任务
            </el-button>
          </template>
        </el-table-column>
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
    </el-card>

    <el-drawer
      v-model="detailDrawerVisible"
      title="任务详情"
      size="420px"
      append-to-body
    >
      <template v-if="selectedTask">
        <div class="drawer-section">
          <div class="drawer-label">知识库</div>
          <div class="drawer-value">{{ selectedTask.name }}</div>
        </div>
        <div class="drawer-section">
          <div class="drawer-label">任务状态</div>
          <el-tag :type="getStatusType(selectedTask.task.status)">
            {{ getStatusLabel(selectedTask.task.status) }}
          </el-tag>
        </div>
        <div class="drawer-section">
          <div class="drawer-label">任务进度</div>
          <el-progress :percentage="formatProgress(selectedTask)" />
          <div class="drawer-hint">{{ selectedTask.task.current || 0 }} / {{ selectedTask.task.total || 0 }}</div>
        </div>
        <div class="drawer-section">
          <div class="drawer-label">开始时间</div>
          <div class="drawer-value">{{ formatStartTime(selectedTask.task.start_time) }}</div>
        </div>
        <div class="drawer-section">
          <div class="drawer-label">最新消息</div>
          <el-alert :title="selectedTask.task.message || '暂无日志信息'" type="info" :closable="false" />
        </div>
        <div class="drawer-actions">
          <el-button @click="openKnowledgeBaseDetail(selectedTask)">
            打开知识库
          </el-button>
          <el-button
            type="primary"
            :disabled="selectedTask.task.status === 'running' || selectedTask.task.status === 'starting'"
            @click="handleStartTask(selectedTask)"
          >
            重新启动
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
.page-card {
  border-radius: 12px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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

.filter-bar {
  margin-bottom: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.summary-card {
  border-radius: 10px;
}

.summary-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.summary-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);

  &.success {
    color: var(--el-color-success);
  }

  &.warning {
    color: var(--el-color-warning);
  }

  &.danger {
    color: var(--el-color-danger);
  }

  &.info {
    color: var(--el-color-primary);
  }
}

.task-table {
  margin-top: 8px;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.drawer-section {
  margin-bottom: 20px;
}

.drawer-label {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.drawer-value {
  font-size: 14px;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.drawer-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.drawer-actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}
</style>
