<script lang="ts" setup>
import { getOverviewStatsApi } from "@@/apis/stats"

defineOptions({
  name: "Overview"
})

const loading = ref(false)
const stats = reactive({
  orgCount: 0,
  userCount: 0,
  kbCount: 0,
  fileCount: 0,
  totalFileSize: 0
})

function formatSize(bytes: number) {
  if (!bytes) return "0 B"
  if (bytes < 1024) return bytes + " B"
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB"
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + " GB"
}

function loadStats() {
  loading.value = true
  getOverviewStatsApi()
    .then((res: any) => {
      if (res.data) Object.assign(stats, res.data)
    })
    .catch(() => {})
    .finally(() => { loading.value = false })
}

onMounted(loadStats)

const cards = computed(() => [
  { label: "组织总数", value: stats.orgCount, icon: "ri-organization-chart", color: "#409eff" },
  { label: "用户总数", value: stats.userCount, icon: "ri-user-line", color: "#67c23a" },
  { label: "知识库总数", value: stats.kbCount, icon: "ri-book-open-line", color: "#e6a23c" },
  { label: "文件总数", value: stats.fileCount, icon: "ri-file-list-line", color: "#f56c6c", extra: formatSize(stats.totalFileSize) }
])
</script>

<template>
  <div class="app-container">
    <div v-loading="loading" class="overview-grid">
      <div v-for="card in cards" :key="card.label" class="stat-card" :style="{ borderTopColor: card.color }">
        <div class="stat-icon" :style="{ backgroundColor: card.color + '15', color: card.color }">
          <span class="stat-icon-text">{{ card.label.charAt(0) }}</span>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
          <div v-if="card.extra" class="stat-extra">{{ card.extra }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  border-top: 3px solid;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-text {
  font-size: 22px;
  font-weight: 700;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.stat-extra {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 2px;
}
</style>
