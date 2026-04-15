<script lang="ts" setup>
import type { FormInstance } from "element-plus"
import {
  addTeamMemberApi,
  createTeamApi,
  deleteTeamApi,
  getOrgTreeApi,
  getOrgKnowledgebasesApi,
  getOrgFilesApi,
  getTeamMembersApi,
  getUsersApi,
  removeTeamMemberApi,
  updateMemberRoleApi,
  updateTeamApi
} from "@@/apis/teams"
import { createKnowledgeBaseApi } from "@@/apis/kbs/knowledgebase"
import { uploadFileApiV2 } from "@@/apis/files/upload"
import { addDocumentToKnowledgeBaseApi } from "@@/apis/kbs/knowledgebase"
import { startDocumentParse, getDocumentParseProgress } from "@@/apis/kbs/document"
import { CirclePlus, Delete, Refresh, Search, ArrowLeft, Edit, MoreFilled, Upload, Setting, VideoPlay } from "@element-plus/icons-vue"

defineOptions({
  name: "TeamManagement"
})

const ROLE_MAP: Record<string, string> = {
  owner: "拥有者",
  admin: "管理员",
  editor: "编辑者",
  viewer: "只读"
}
const EDITABLE_ROLES = [
  { value: "admin", label: "管理员" },
  { value: "editor", label: "编辑者" },
  { value: "viewer", label: "只读" }
]

interface OrgNode {
  id: string
  name: string
  ownerName: string
  memberCount: number
  kbCount: number
  fileCount: number
  description: string
  parentId: string | null
  ownerId?: string
  createTime: string
  children: OrgNode[]
}
interface TeamMember { userId: string; username: string; email: string; role: string; joinTime: string; orgNames?: string[]; isDescendant?: boolean }
interface KbItem { id: string; name: string; description: string; docNum: number; tokenNum: number; chunkNum: number; creatorName: string; createTime: string; orgName?: string; isDescendant?: boolean }
interface FileItem { id: string; name: string; size: number; type: string; run: string; progress: number; kbName: string; createTime: string; orgName?: string; isDescendant?: boolean }

// ==================== 视图状态 ====================
const currentView = ref<string>("tree")
const selectedOrg = ref<OrgNode | null>(null)

function openDetail(row: OrgNode, view: string) {
  selectedOrg.value = row
  currentView.value = view
  if (view === "members") fetchMembers(row.id)
  else if (view === "kbs") fetchKbs(row.id)
  else if (view === "files") fetchFiles(row.id)
}

function goBack() {
  currentView.value = "tree"
  selectedOrg.value = null
}

// ==================== 树数据 ====================
const loading = ref(false)
const treeData = ref<OrgNode[]>([])
const searchKeyword = ref("")

function loadTree() {
  loading.value = true
  getOrgTreeApi()
    .then((res: any) => { treeData.value = res.data || []; setupRowDraggable() })
    .catch(() => { treeData.value = [] })
    .finally(() => { loading.value = false })
}

function filterTree(nodes: OrgNode[], keyword: string): OrgNode[] {
  if (!keyword) return nodes
  const lowerKw = keyword.toLowerCase()
  return nodes.reduce<OrgNode[]>((acc, node) => {
    const filteredChildren = filterTree(node.children || [], keyword)
    if (node.name.toLowerCase().includes(lowerKw) || filteredChildren.length > 0) {
      acc.push({ ...node, children: filteredChildren })
    }
    return acc
  }, [])
}
const filteredTreeData = computed(() => filterTree(treeData.value, searchKeyword.value))
const defaultExpandKeys = computed(() => treeData.value.map(n => n.id))
onMounted(loadTree)

// ==================== 拖拽 ====================
const draggedOrg = ref<OrgNode | null>(null)

function findOrgById(nodes: OrgNode[], id: string): OrgNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    const found = findOrgById(n.children || [], id)
    if (found) return found
  }
  return null
}

function isDescendant(ancestor: OrgNode, targetId: string): boolean {
  for (const c of (ancestor.children || [])) {
    if (c.id === targetId) return true
    if (isDescendant(c, targetId)) return true
  }
  return false
}

function getRowClassName({ row }: { row: OrgNode }) {
  return `drag-row drag-row-${row.id}`
}

function setupRowDraggable() {
  nextTick(() => {
    const rows = document.querySelectorAll(".drag-row")
    rows.forEach((tr) => {
      tr.setAttribute("draggable", "true")
    })
  })
}

function handleDragStart(e: DragEvent) {
  const target = e.target as HTMLElement
  // 如果点击的是按钮、链接、图标等交互元素，不触发拖拽
  if (target.closest("button, a, .el-button, .el-dropdown, .count-link, .el-icon")) {
    e.preventDefault()
    return
  }
  const tr = target.closest("tr")
  if (!tr) return
  const match = tr.className.match(/drag-row-([\da-f]+)/)
  if (!match) return
  const row = findOrgById(treeData.value, match[1])
  if (!row) return
  draggedOrg.value = row
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move"
    e.dataTransfer.setData("text/plain", row.id)
  }
}

function handleTableDragOver(e: DragEvent) {
  e.preventDefault()
  if (!e.dataTransfer) return
  e.dataTransfer.dropEffect = "move"
  // 高亮当前行
  const tr = (e.target as HTMLElement).closest("tr")
  if (!tr) return
  // 清除其他高亮
  document.querySelectorAll(".drag-over").forEach(el => el.classList.remove("drag-over"))
  tr.classList.add("drag-over")
}

function handleTableDragLeave(e: DragEvent) {
  const tr = (e.target as HTMLElement).closest("tr")
  if (tr) tr.classList.remove("drag-over")
}

function handleTableDrop(e: DragEvent) {
  e.preventDefault()
  document.querySelectorAll(".drag-over").forEach(el => el.classList.remove("drag-over"))
  if (!draggedOrg.value) return

  const tr = (e.target as HTMLElement).closest("tr")
  if (!tr) return

  const match = tr.className.match(/drag-row-([\da-f]+)/)
  if (!match) return

  const targetId = match[1]
  const dragged = draggedOrg.value
  draggedOrg.value = null

  if (dragged.id === targetId) return
  if (isDescendant(dragged, targetId)) {
    ElMessage.warning("不能移动到自身的子组织下")
    return
  }

  const targetOrg = findOrgById(treeData.value, targetId)
  if (!targetOrg) return

  ElMessageBox.confirm(`确认将「${dragged.name}」移动到「${targetOrg.name}」下？`, "移动组织", {
    confirmButtonText: "确定", cancelButtonText: "取消", type: "info"
  }).then(() => {
    updateTeamApi(dragged.id, { parent_id: targetId })
      .then(() => { ElMessage.success("移动成功"); loadTree() })
      .catch(() => { ElMessage.error("移动失败") })
  })
}

// ==================== 成员 ====================
const teamMembers = ref<TeamMember[]>([])
const memberLoading = ref(false)

function fetchMembers(teamId: string) {
  memberLoading.value = true
  getTeamMembersApi(teamId as any)
    .then((res: any) => {
      if (res.data && Array.isArray(res.data.list)) teamMembers.value = res.data.list
      else if (Array.isArray(res.data)) teamMembers.value = res.data
      else teamMembers.value = []
    })
    .catch(() => { teamMembers.value = [] })
    .finally(() => { memberLoading.value = false })
}

function handleRoleChange(member: TeamMember, newRole: string) {
  if (!selectedOrg.value) return
  updateMemberRoleApi(selectedOrg.value.id, member.userId, newRole)
    .then(() => { ElMessage.success("角色修改成功"); fetchMembers(selectedOrg.value!.id) })
    .catch(() => { ElMessage.error("角色修改失败"); fetchMembers(selectedOrg.value!.id) })
}

function handleRemoveMember(member: TeamMember) {
  ElMessageBox.confirm(`确认将「${member.username}」从组织中移除吗？`, "提示", {
    confirmButtonText: "确定", cancelButtonText: "取消", type: "warning"
  }).then(() => {
    if (!selectedOrg.value) return
    removeTeamMemberApi({ teamId: selectedOrg.value.id as any, memberId: member.userId as any })
      .then(() => { ElMessage.success("成员移除成功"); fetchMembers(selectedOrg.value!.id); loadTree() })
  })
}

// ==================== 添加成员 ====================
const addMemberDialogVisible = ref(false)
const userList = ref<{ id: string; username: string }[]>([])
const userLoading = ref(false)
const selectedUser = ref<string | undefined>(undefined)
const selectedRole = ref("viewer")
const availableUsers = computed(() => {
  const memberIds = new Set(teamMembers.value.map((m) => m.userId))
  return userList.value.filter((u) => !memberIds.has(u.id))
})

function handleAddMember() {
  addMemberDialogVisible.value = true
  selectedUser.value = undefined
  selectedRole.value = "viewer"
  userLoading.value = true
  getUsersApi({ size: 99999 })
    .then((res: any) => { userList.value = res.data?.list || [] })
    .catch(() => { userList.value = [] })
    .finally(() => { userLoading.value = false })
}

function confirmAddMember() {
  if (!selectedUser.value) { ElMessage.warning("请选择要添加的用户"); return }
  if (!selectedOrg.value) return
  addTeamMemberApi({ teamId: selectedOrg.value.id as any, userId: selectedUser.value as any, role: selectedRole.value })
    .then(() => {
      ElMessage.success("添加成员成功")
      addMemberDialogVisible.value = false
      fetchMembers(selectedOrg.value!.id)
      loadTree()
    })
    .catch(() => { ElMessage.error("添加成员失败") })
}

// ==================== 知识库 ====================
const kbList = ref<KbItem[]>([])
const kbLoading = ref(false)

function fetchKbs(orgId: string) {
  kbLoading.value = true
  getOrgKnowledgebasesApi(orgId)
    .then((res: any) => { kbList.value = Array.isArray(res.data) ? res.data : [] })
    .catch(() => { kbList.value = [] })
    .finally(() => { kbLoading.value = false })
}

// ==================== 文件 ====================
const fileList = ref<FileItem[]>([])
const fileLoading = ref(false)

function fetchFiles(orgId: string) {
  fileLoading.value = true
  getOrgFilesApi(orgId)
    .then((res: any) => { fileList.value = Array.isArray(res.data) ? res.data : [] })
    .catch(() => { fileList.value = [] })
    .finally(() => { fileLoading.value = false })
}

function formatSize(bytes: number) {
  if (!bytes) return "0"
  if (bytes < 1024) return bytes + " B"
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
  return (bytes / 1024 / 1024).toFixed(1) + " MB"
}

// ==================== 创建知识库 ====================
const createKbDialogVisible = ref(false)
const createKbLoading = ref(false)
const createKbForm = reactive({ name: "", description: "" })

function handleCreateKb() {
  createKbForm.name = ""
  createKbForm.description = ""
  createKbDialogVisible.value = true
}

function confirmCreateKb() {
  if (!createKbForm.name.trim()) { ElMessage.warning("请输入知识库名称"); return }
  if (!selectedOrg.value) return
  createKbLoading.value = true
  createKnowledgeBaseApi({
    name: createKbForm.name,
    description: createKbForm.description,
    org_id: selectedOrg.value.id
  } as any)
    .then(() => {
      ElMessage.success("知识库创建成功")
      createKbDialogVisible.value = false
      fetchKbs(selectedOrg.value!.id)
      loadTree()
    })
    .catch(() => { ElMessage.error("创建知识库失败") })
    .finally(() => { createKbLoading.value = false })
}

// ==================== 上传文件 ====================
const uploadDialogVisible = ref(false)
const uploadLoading = ref(false)
const uploadKbId = ref<string | undefined>(undefined)
const uploadFiles = ref<File[]>([])

function handleUploadFile() {
  uploadKbId.value = undefined
  uploadFiles.value = []
  uploadDialogVisible.value = true
  if (selectedOrg.value) fetchKbs(selectedOrg.value.id)
}

function onFileChange(file: any) {
  uploadFiles.value.push(file.raw)
}

function onFileRemove(file: any) {
  uploadFiles.value = uploadFiles.value.filter(f => f.name !== file.name)
}

function confirmUploadFile() {
  if (!uploadKbId.value) { ElMessage.warning("请选择目标知识库"); return }
  if (uploadFiles.value.length === 0) { ElMessage.warning("请选择要上传的文件"); return }
  uploadLoading.value = true
  const formData = new FormData()
  uploadFiles.value.forEach(f => formData.append("files", f))
  uploadFileApiV2(formData)
    .then((res: any) => {
      const fileIds = (res.data || []).map((f: any) => f.id).filter(Boolean)
      if (fileIds.length === 0) { ElMessage.error("上传失败"); return }
      return addDocumentToKnowledgeBaseApi({ kb_id: uploadKbId.value!, file_ids: fileIds })
    })
    .then(() => {
      ElMessage.success("文件上传成功")
      uploadDialogVisible.value = false
      if (selectedOrg.value) fetchFiles(selectedOrg.value.id)
      loadTree()
    })
    .catch(() => { ElMessage.error("上传失败") })
    .finally(() => { uploadLoading.value = false })
}

// ==================== 创建/编辑组织 ====================
const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance | null>(null)
const createLoading = ref(false)
const parentLocked = ref(false)
const isEdit = ref(false)
const editingOrgId = ref("")
const createFormData = reactive({
  name: "",
  description: "",
  owner_id: undefined as string | undefined,
  parent_id: undefined as string | undefined
})
const ownerUserList = ref<{ id: string; username: string }[]>([])

function getFilteredTreeForEdit(nodes: OrgNode[], excludeId: string): OrgNode[] {
  return nodes.reduce<OrgNode[]>((acc, node) => {
    if (node.id === excludeId) return acc
    const filtered = getFilteredTreeForEdit(node.children || [], excludeId)
    acc.push({ ...node, children: filtered })
    return acc
  }, [])
}
const editTreeData = computed(() => {
  if (isEdit.value && editingOrgId.value) {
    return getFilteredTreeForEdit(treeData.value, editingOrgId.value)
  }
  return treeData.value
})

function handleOpenCreate() {
  isEdit.value = false
  parentLocked.value = false
  createFormData.name = ""
  createFormData.description = ""
  createFormData.owner_id = undefined
  createFormData.parent_id = undefined
  createDialogVisible.value = true
  fetchOwnerUsers()
}

function handleAddChild(row: OrgNode) {
  isEdit.value = false
  parentLocked.value = true
  createFormData.name = ""
  createFormData.description = ""
  createFormData.owner_id = undefined
  createFormData.parent_id = row.id
  createDialogVisible.value = true
  fetchOwnerUsers()
}

function handleEdit(row: OrgNode) {
  isEdit.value = true
  editingOrgId.value = row.id
  parentLocked.value = false
  createFormData.name = row.name
  createFormData.description = row.description || ""
  createFormData.owner_id = row.ownerId || undefined
  createFormData.parent_id = row.parentId || undefined
  createDialogVisible.value = true
  fetchOwnerUsers()
}

function fetchOwnerUsers() {
  getUsersApi({ size: 99999 }).then((res: any) => {
    if (res.data) ownerUserList.value = res.data.list
  })
}

function handleSaveOrg() {
  createFormRef.value?.validate((valid) => {
    if (!valid) return
    createLoading.value = true
    if (isEdit.value) {
      updateTeamApi(editingOrgId.value, {
        name: createFormData.name,
        description: createFormData.description,
        owner_id: createFormData.owner_id,
        parent_id: createFormData.parent_id || null
      })
        .then(() => { ElMessage.success("组织更新成功"); createDialogVisible.value = false; loadTree() })
        .catch(() => { ElMessage.error("组织更新失败") })
        .finally(() => { createLoading.value = false })
    } else {
      createTeamApi({
        name: createFormData.name,
        description: createFormData.description,
        owner_id: createFormData.owner_id,
        parent_id: createFormData.parent_id
      })
        .then(() => { ElMessage.success("创建组织成功"); createDialogVisible.value = false; loadTree() })
        .catch(() => { ElMessage.error("创建组织失败") })
        .finally(() => { createLoading.value = false })
    }
  })
}

function handleDelete(row: OrgNode) {
  const hasChildren = row.children && row.children.length > 0
  const msg = hasChildren
    ? `确认删除「${row.name}」及其所有子组织？此操作不可恢复。`
    : `确认删除组织「${row.name}」？此操作将同时移除所有成员关联。`
  ElMessageBox.confirm(msg, "提示", {
    confirmButtonText: "确定", cancelButtonText: "取消", type: "warning"
  }).then(() => {
    deleteTeamApi(row.id)
      .then(() => { ElMessage.success("删除成功"); loadTree() })
      .catch(() => { ElMessage.error("删除失败") })
  })
}

// ==================== 解析配置 ====================
const parseConfigDialogVisible = ref(false)
const parseLoading = ref(false)
const currentParseFile = ref<FileItem | null>(null)
const parseConfig = reactive({
  ocr_mode: "auto" as "auto" | "force_ocr" | "force_text",
  extract_images: true,
  chunk_strategy: "paragraph" as "paragraph" | "page" | "custom",
  chunk_max_length: 500
})

function handleParseConfig(file: FileItem) {
  currentParseFile.value = file
  parseConfig.ocr_mode = "auto"
  parseConfig.extract_images = true
  parseConfig.chunk_strategy = "paragraph"
  parseConfig.chunk_max_length = 500
  parseConfigDialogVisible.value = true
}

function handleQuickParse(file: FileItem) {
  parseLoading.value = true
  startDocumentParse(file.id)
    .then(() => {
      ElMessage.success("解析已开始")
      if (selectedOrg.value) fetchFiles(selectedOrg.value.id)
    })
    .catch(() => { ElMessage.error("解析失败") })
    .finally(() => { parseLoading.value = false })
}

function confirmParse() {
  if (!currentParseFile.value) return
  parseLoading.value = true
  const config = { ...parseConfig }
  if (config.chunk_strategy !== "custom") {
    delete (config as any).chunk_max_length
  }
  startDocumentParse(currentParseFile.value.id, config)
    .then(() => {
      ElMessage.success("解析已开始")
      parseConfigDialogVisible.value = false
      if (selectedOrg.value) fetchFiles(selectedOrg.value.id)
    })
    .catch(() => { ElMessage.error("解析失败") })
    .finally(() => { parseLoading.value = false })
}

// ==================== 解析日志 ====================
const parseLogDialogVisible = ref(false)
const parseLogFile = ref<FileItem | null>(null)
const parseLogMessage = ref("")
const parseLogProgress = ref(0)
const parseLogTimer = ref<any>(null)

function handleViewParseLog(file: FileItem) {
  parseLogFile.value = file
  parseLogMessage.value = ""
  parseLogProgress.value = file.progress || 0
  parseLogDialogVisible.value = true
  pollParseLog(file.id)
}

function pollParseLog(docId: string) {
  if (parseLogTimer.value) clearInterval(parseLogTimer.value)
  const fetchLog = () => {
    getDocumentParseProgress(docId)
      .then((res: any) => {
        const data = res.data || {}
        parseLogMessage.value = data.message || ""
        parseLogProgress.value = data.progress || 0
        if (data.progress >= 1 || data.run === "0" || data.run === "3") {
          clearInterval(parseLogTimer.value)
          parseLogTimer.value = null
        }
      })
      .catch(() => {})
  }
  fetchLog()
  parseLogTimer.value = setInterval(fetchLog, 2000)
}

watch(parseLogDialogVisible, (val) => {
  if (!val && parseLogTimer.value) {
    clearInterval(parseLogTimer.value)
    parseLogTimer.value = null
  }
})

function handleDropdownCommand(command: string, row: OrgNode) {
  if (command === "members") openDetail(row, "members")
  else if (command === "kbs") openDetail(row, "kbs")
  else if (command === "files") openDetail(row, "files")
  else if (command === "delete") handleDelete(row)
}
</script>

<template>
  <div class="app-container">

    <!-- ====== 视图1: 组织树 ====== -->
    <template v-if="currentView === 'tree'">
      <el-card v-loading="loading" shadow="never">
        <div class="toolbar-wrapper">
          <el-button type="primary" :icon="CirclePlus" @click="handleOpenCreate">创建组织</el-button>
          <div class="toolbar-right">
            <el-input v-model="searchKeyword" placeholder="搜索组织名称" :prefix-icon="Search" clearable style="width: 240px" />
            <el-button :icon="Refresh" circle @click="loadTree" />
          </div>
        </div>
        <el-table
          :data="filteredTreeData"
          row-key="id"
          :tree-props="{ children: 'children' }"
          :default-expand-all="false"
          :expand-row-keys="defaultExpandKeys"
          :row-class-name="getRowClassName"
          border
          @dragstart="handleDragStart"
          @dragover.prevent="handleTableDragOver"
          @dragleave="handleTableDragLeave"
          @drop="handleTableDrop"
        >
          <el-table-column prop="name" label="组织名称" min-width="200" />
          <el-table-column prop="ownerName" label="负责人" width="120" align="center" />
          <el-table-column label="成员" width="80" align="center">
            <template #default="{ row }">
              <span class="count-link" @click="openDetail(row, 'members')">{{ row.memberCount }}</span>
            </template>
          </el-table-column>
          <el-table-column label="知识库" width="80" align="center">
            <template #default="{ row }">
              <span class="count-link" @click="openDetail(row, 'kbs')">{{ row.kbCount }}</span>
            </template>
          </el-table-column>
          <el-table-column label="文件" width="80" align="center">
            <template #default="{ row }">
              <span class="count-link" @click="openDetail(row, 'files')">{{ row.fileCount }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
          <el-table-column prop="createTime" label="创建时间" width="170" align="center" />
          <el-table-column fixed="right" label="操作" width="220" align="center">
            <template #default="{ row }">
              <el-button type="primary" text bg size="small" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
              <el-button type="primary" text bg size="small" :icon="CirclePlus" @click="handleAddChild(row)">子组织</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => handleDropdownCommand(cmd, row)">
                <el-button type="info" text bg size="small" :icon="MoreFilled" style="margin-left: 8px" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="members">成员管理</el-dropdown-item>
                    <el-dropdown-item command="kbs">知识库</el-dropdown-item>
                    <el-dropdown-item command="files">文件列表</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <span style="color: var(--el-color-danger)">删除组织</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- ====== 视图2: 成员列表 ====== -->
    <template v-else-if="currentView === 'members' && selectedOrg">
      <el-card shadow="never">
        <div class="detail-toolbar">
          <div class="detail-back">
            <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
            <span class="detail-title">{{ selectedOrg.name }} - 成员列表</span>
          </div>
          <el-button type="primary" :icon="CirclePlus" @click="handleAddMember">添加成员</el-button>
        </div>
        <el-table :data="teamMembers" v-loading="memberLoading" style="width: 100%">
          <el-table-column prop="username" label="用户名" align="center" />
          <el-table-column prop="email" label="邮箱" align="center" />
          <el-table-column label="所属组织" min-width="180" align="center">
            <template #default="{ row }">
              <el-tag v-for="name in (row.orgNames || [])" :key="name" size="small" style="margin: 2px" :type="name === selectedOrg?.name ? '' : 'info'">{{ name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="140" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.role === 'owner'" type="warning" size="small">{{ ROLE_MAP[row.role] }}</el-tag>
              <el-select v-else :model-value="row.role" size="small" style="width: 100px" @change="(val: string) => handleRoleChange(row, val)">
                <el-option v-for="r in EDITABLE_ROLES" :key="r.value" :label="r.label" :value="r.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column prop="joinTime" label="加入时间" width="170" align="center" />
          <el-table-column fixed="right" label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button type="danger" text bg size="small" :disabled="row.role === 'owner'" @click="handleRemoveMember(row)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="teamMembers.length === 0 && !memberLoading" description="暂无成员" />
      </el-card>
    </template>

    <!-- ====== 视图3: 知识库卡片 ====== -->
    <template v-else-if="currentView === 'kbs' && selectedOrg">
      <el-card shadow="never">
        <div class="detail-toolbar">
          <div class="detail-back">
            <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
            <span class="detail-title">{{ selectedOrg.name }} - 知识库</span>
          </div>
          <el-button type="primary" :icon="CirclePlus" @click="handleCreateKb">创建知识库</el-button>
        </div>
        <div v-loading="kbLoading">
          <div v-if="kbList.length > 0" class="kb-card-grid">
            <el-card v-for="kb in kbList" :key="kb.id" shadow="hover" class="kb-card">
              <template #header>
                <div class="kb-card-header">
                  <span class="kb-card-title">{{ kb.name }}</span>
                  <el-tag v-if="kb.isDescendant" type="info" size="small">{{ kb.orgName }}</el-tag>
                </div>
              </template>
              <p v-if="kb.description" class="kb-desc">{{ kb.description }}</p>
              <div class="kb-meta">
                <span>文档: {{ kb.docNum }}</span>
                <span>分块: {{ kb.chunkNum }}</span>
                <span>创建者: {{ kb.creatorName }}</span>
              </div>
              <div class="kb-time">{{ kb.createTime }}</div>
            </el-card>
          </div>
          <el-empty v-else description="暂无知识库" />
        </div>
      </el-card>
    </template>

    <!-- ====== 视图4: 文件列表 ====== -->
    <template v-else-if="currentView === 'files' && selectedOrg">
      <el-card shadow="never">
        <div class="detail-toolbar">
          <div class="detail-back">
            <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
            <span class="detail-title">{{ selectedOrg.name }} - 文件列表</span>
          </div>
          <el-button type="primary" :icon="Upload" @click="handleUploadFile">上传文件</el-button>
        </div>
        <div v-loading="fileLoading">
          <el-table v-if="fileList.length > 0" :data="fileList" style="width: 100%">
            <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column label="所属组织" width="180" align="center">
              <template #default="{ row }">
                <span>{{ row.orgName }}</span>
                <el-tag v-if="row.isDescendant" type="info" size="small" style="margin-left: 4px">子</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="100" align="center">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="kbName" label="所属知识库" width="150" show-overflow-tooltip />
            <el-table-column label="解析进度" width="120" align="center">
              <template #default="{ row }">
                <el-progress v-if="row.progress > 0 && row.progress < 1" :percentage="Math.round(row.progress * 100)" :stroke-width="6" />
                <el-tag v-else-if="row.progress >= 1" type="success" size="small">已完成</el-tag>
                <el-tag v-else type="info" size="small">未解析</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="170" align="center" />
            <el-table-column fixed="right" label="操作" width="220" align="center">
              <template #default="{ row }">
                <el-button type="primary" text bg size="small" :icon="VideoPlay" :disabled="row.progress > 0 && row.progress < 1" @click="handleQuickParse(row)">解析</el-button>
                <el-button type="warning" text bg size="small" :icon="Setting" @click="handleParseConfig(row)">配置</el-button>
                <el-button v-if="row.progress > 0" type="info" text bg size="small" @click="handleViewParseLog(row)">日志</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无文件" />
        </div>
      </el-card>
    </template>

    <!-- 创建/编辑组织弹窗 -->
    <el-dialog v-model="createDialogVisible" :title="isEdit ? '编辑组织' : (parentLocked ? '添加子组织' : '创建组织')" width="480px" destroy-on-close>
      <el-form ref="createFormRef" :model="createFormData" label-width="80px">
        <el-form-item label="组织名称" prop="name" :rules="[{ required: true, message: '请输入组织名称', trigger: 'blur' }]">
          <el-input v-model="createFormData.name" placeholder="如：电力运维部" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createFormData.description" type="textarea" :rows="2" placeholder="组织描述（可选）" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="createFormData.owner_id" placeholder="不选则为当前用户" style="width: 100%" filterable clearable>
            <el-option v-for="user in ownerUserList" :key="user.id" :label="user.username" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级组织">
          <el-tree-select
            v-model="createFormData.parent_id"
            :data="editTreeData"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="不选则为根组织"
            check-strictly clearable
            :disabled="parentLocked"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleSaveOrg">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- 添加成员弹窗 -->
    <el-dialog v-model="addMemberDialogVisible" title="添加成员" width="400px" destroy-on-close>
      <div v-loading="userLoading">
        <el-form label-width="80px">
          <el-form-item label="选择用户">
            <el-select v-model="selectedUser" :placeholder="availableUsers.length > 0 ? '请选择用户' : '(无可添加的用户)'" style="width: 100%" :disabled="availableUsers.length === 0" filterable>
              <el-option v-for="user in availableUsers" :key="user.id" :label="user.username" :value="user.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="selectedRole" style="width: 100%">
              <el-option v-for="r in EDITABLE_ROLES" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedUser" @click="confirmAddMember">确认</el-button>
      </template>
    </el-dialog>

    <!-- 创建知识库弹窗 -->
    <el-dialog v-model="createKbDialogVisible" title="创建知识库" width="440px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="createKbForm.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createKbForm.description" type="textarea" :rows="2" placeholder="知识库描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createKbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createKbLoading" @click="confirmCreateKb">创建</el-button>
      </template>
    </el-dialog>

    <!-- 上传文件弹窗 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="500px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="目标知识库" required>
          <el-select v-model="uploadKbId" placeholder="选择知识库" style="width: 100%" filterable>
            <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            :auto-upload="false"
            multiple
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-button type="primary" plain>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploadLoading" @click="confirmUploadFile">上传</el-button>
      </template>
    </el-dialog>

    <!-- 解析配置弹窗 -->
    <el-dialog v-model="parseConfigDialogVisible" title="解析配置" width="480px" destroy-on-close>
      <div v-if="currentParseFile" style="margin-bottom: 16px; color: var(--el-text-color-secondary); font-size: 13px;">
        文件: {{ currentParseFile.name }}
      </div>
      <el-form label-width="100px">
        <el-form-item label="OCR模式">
          <el-radio-group v-model="parseConfig.ocr_mode">
            <el-radio value="auto">自动检测</el-radio>
            <el-radio value="force_ocr">强制OCR</el-radio>
            <el-radio value="force_text">强制文本</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="提取图片">
          <el-switch v-model="parseConfig.extract_images" />
        </el-form-item>
        <el-form-item label="分块策略">
          <el-radio-group v-model="parseConfig.chunk_strategy">
            <el-radio value="paragraph">按段落</el-radio>
            <el-radio value="page">按页面</el-radio>
            <el-radio value="custom">自定义长度</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="parseConfig.chunk_strategy === 'custom'" label="最大长度">
          <el-input-number v-model="parseConfig.chunk_max_length" :min="100" :max="10000" :step="100" />
          <span style="margin-left: 8px; color: var(--el-text-color-secondary); font-size: 12px;">字符</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="parseConfigDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="parseLoading" @click="confirmParse">开始解析</el-button>
      </template>
    </el-dialog>

    <!-- 解析日志弹窗 -->
    <el-dialog v-model="parseLogDialogVisible" title="解析日志" width="560px" destroy-on-close>
      <div v-if="parseLogFile" style="margin-bottom: 12px; font-size: 13px; color: var(--el-text-color-secondary);">
        文件: {{ parseLogFile.name }}
      </div>
      <el-progress :percentage="Math.round(parseLogProgress * 100)" :stroke-width="10" style="margin-bottom: 16px;" />
      <div class="parse-log-box">
        <div v-if="parseLogMessage" class="parse-log-content">{{ parseLogMessage }}</div>
        <div v-else style="color: var(--el-text-color-placeholder); text-align: center; padding: 20px;">暂无日志信息</div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.count-link {
  color: var(--el-color-primary);
  cursor: pointer;
  font-weight: 500;
  &:hover { text-decoration: underline; }
}

// 整行拖拽
:deep(tr.drag-row) {
  cursor: grab;
  &:active { cursor: grabbing; }
  .el-button, .el-dropdown, .count-link {
    cursor: pointer;
  }
}

// 拖拽高亮
:deep(tr.drag-over) {
  td {
    background-color: var(--el-color-primary-light-8) !important;
    border-top: 2px solid var(--el-color-primary) !important;
  }
}

// 详情页
.detail-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.detail-back {
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-title {
  font-size: 16px;
  font-weight: 600;
}

// 知识库卡片
.kb-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.kb-card {
  .kb-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .kb-card-title {
    font-weight: 600;
    font-size: 14px;
  }
  .kb-desc {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 8px;
  }
  .kb-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--el-text-color-regular);
  }
  .kb-time {
    margin-top: 8px;
    font-size: 11px;
    color: var(--el-text-color-placeholder);
  }
}

// 解析日志
.parse-log-box {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
  font-family: "Courier New", monospace;
}
.parse-log-content {
  font-size: 13px;
  line-height: 1.8;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
