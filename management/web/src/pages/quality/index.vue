<script lang="ts" setup>
import ConversationPage from "@/pages/conversation/index.vue"
import { DataAnalysis, ChatDotRound } from "@element-plus/icons-vue"

defineOptions({
  name: "QualityCenter"
})

const activeTab = ref("conversation")

const plannedItems = [
  "评测数据集管理",
  "批量问答运行与结果留档",
  "准确率、BLEU、ROUGE-L 汇总报表",
  "对话与知识库引用关联分析"
]
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="quality-card">
      <template #header>
        <div class="page-header">
          <div>
            <div class="page-title">对话与评测</div>
            <div class="page-subtitle">先接入对话审计主流程，评测报表在 V1 中以结果面板形式逐步补齐。</div>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane name="conversation" label="对话审计" lazy>
          <template #label>
            <span class="tab-label">
              <el-icon><ChatDotRound /></el-icon>
              <span>对话审计</span>
            </span>
          </template>
          <ConversationPage />
        </el-tab-pane>

        <el-tab-pane name="evaluation" label="评测报表">
          <template #label>
            <span class="tab-label">
              <el-icon><DataAnalysis /></el-icon>
              <span>评测报表</span>
            </span>
          </template>

          <div class="evaluation-placeholder">
            <el-row :gutter="16">
              <el-col :md="12" :sm="24">
                <el-card shadow="hover" class="placeholder-card">
                  <template #header>
                    <div class="placeholder-title">V1 当前状态</div>
                  </template>
                  <el-alert
                    title="管理后台已正式接入“对话与评测”菜单，但评测接口仍待聚合到 management 后端。"
                    type="info"
                    :closable="false"
                    show-icon
                  />
                  <ul class="planned-list">
                    <li v-for="item in plannedItems" :key="item">
                      {{ item }}
                    </li>
                  </ul>
                </el-card>
              </el-col>

              <el-col :md="12" :sm="24">
                <el-card shadow="hover" class="placeholder-card">
                  <template #header>
                    <div class="placeholder-title">落地建议</div>
                  </template>
                  <div class="hint-group">
                    <div class="hint-item">
                      <div class="hint-label">第一阶段</div>
                      <div class="hint-value">完成评测结果只读展示，优先接入准确率和最近运行记录。</div>
                    </div>
                    <div class="hint-item">
                      <div class="hint-label">第二阶段</div>
                      <div class="hint-value">补评测数据集管理与批量运行入口。</div>
                    </div>
                    <div class="hint-item">
                      <div class="hint-label">第三阶段</div>
                      <div class="hint-value">把评测结果和知识库详情、会话审计打通。</div>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.quality-card {
  border-radius: 12px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
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

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.evaluation-placeholder {
  padding-top: 12px;
}

.placeholder-card {
  min-height: 280px;
  border-radius: 12px;
}

.placeholder-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.planned-list {
  margin: 18px 0 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);

  li + li {
    margin-top: 10px;
  }
}

.hint-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hint-item {
  padding: 14px 16px;
  background: var(--el-fill-color-light);
  border-radius: 10px;
}

.hint-label {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.hint-value {
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}
</style>
