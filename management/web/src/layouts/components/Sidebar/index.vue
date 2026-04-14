<script lang="ts" setup>
import { useAppStore } from "@/pinia/stores/app"
import { usePermissionStore } from "@/pinia/stores/permission"
import { useSettingsStore } from "@/pinia/stores/settings"
import { useUserStore } from "@/pinia/stores/user"
import { useDevice } from "@@/composables/useDevice"
import { useLayoutMode } from "@@/composables/useLayoutMode"
import { getCssVar } from "@@/utils/css"
import { Expand, Fold, SwitchButton } from "@element-plus/icons-vue"
import { Logo } from "../index"
import Item from "./Item.vue"

const v3SidebarMenuBgColor = getCssVar("--v3-sidebar-menu-bg-color")
const v3SidebarMenuTextColor = getCssVar("--v3-sidebar-menu-text-color")
const v3SidebarMenuActiveTextColor = getCssVar("--v3-sidebar-menu-active-text-color")

const { isMobile } = useDevice()
const { isLeft, isTop } = useLayoutMode()
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const permissionStore = usePermissionStore()
const settingsStore = useSettingsStore()
const userStore = useUserStore()

const activeMenu = computed(() => route.meta.activeMenu || route.path)
const noHiddenRoutes = computed(() => permissionStore.routes.filter(item => !item.meta?.hidden))
const isCollapse = computed(() => !appStore.sidebar.opened)
const isLogo = computed(() => isLeft.value && settingsStore.showLogo)
const backgroundColor = computed(() => (isLeft.value ? v3SidebarMenuBgColor : undefined))
const textColor = computed(() => (isLeft.value ? v3SidebarMenuTextColor : undefined))
const activeTextColor = computed(() => (isLeft.value ? v3SidebarMenuActiveTextColor : undefined))
const sidebarMenuItemHeight = computed(() => !isTop.value ? "var(--v3-sidebar-menu-item-height)" : "var(--v3-navigationbar-height)")
const sidebarMenuHoverBgColor = computed(() => !isTop.value ? "var(--v3-sidebar-menu-hover-bg-color)" : "transparent")
const tipLineWidth = computed(() => !isTop.value ? "2px" : "0px")

function toggleSidebar() {
  appStore.toggleSidebar(false)
}

function logout() {
  userStore.logout()
  router.push("/login")
}
</script>

<template>
  <div class="sidebar-layout" :class="{ 'has-logo': isLogo }">
    <Logo v-if="isLogo" :collapse="isCollapse" />
    <el-scrollbar wrap-class="scrollbar-wrapper" class="menu-scrollbar">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse && !isTop"
        :background-color="backgroundColor"
        :text-color="textColor"
        :active-text-color="activeTextColor"
        :collapse-transition="false"
        :mode="isTop && !isMobile ? 'horizontal' : 'vertical'"
      >
        <Item
          v-for="noHiddenRoute in noHiddenRoutes"
          :key="noHiddenRoute.path"
          :item="noHiddenRoute"
          :base-path="noHiddenRoute.path"
        />
      </el-menu>
    </el-scrollbar>
    <!-- 底部：用户名 + 退出 + 折叠 -->
    <div v-if="isLeft" class="sidebar-footer">
      <div v-if="!isCollapse" class="footer-expanded">
        <el-dropdown>
          <span class="user-info">
            <el-avatar :src="userStore.avatar" :size="28" />
            <span class="user-name">{{ userStore.username }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <div class="collapse-btn" @click="toggleSidebar">
          <el-icon :size="18"><Fold /></el-icon>
        </div>
      </div>
      <div v-else class="footer-collapsed">
        <div class="collapse-btn" @click="toggleSidebar">
          <el-icon :size="18"><Expand /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
%tip-line {
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: v-bind(tipLineWidth);
    height: 100%;
    background-color: var(--v3-sidebar-menu-tip-line-bg-color);
  }
}

.sidebar-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.menu-scrollbar {
  flex: 1;
  overflow: hidden;
}

.has-logo {
  .menu-scrollbar {
    height: calc(100% - var(--v3-header-height) - 50px);
  }
}

.el-scrollbar {
  height: 100%;
  :deep(.scrollbar-wrapper) {
    overflow-x: hidden;
  }
  :deep(.el-scrollbar__bar) {
    &.is-horizontal {
      display: none;
    }
  }
}

.el-menu {
  user-select: none;
  border: none;
  width: 100%;
}

.el-menu--horizontal {
  height: v-bind(sidebarMenuItemHeight);
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title),
:deep(.el-sub-menu .el-menu-item),
:deep(.el-menu--horizontal .el-menu-item) {
  height: v-bind(sidebarMenuItemHeight);
  line-height: v-bind(sidebarMenuItemHeight);
  &.is-active,
  &:hover {
    background-color: v-bind(sidebarMenuHoverBgColor);
  }
}

:deep(.el-sub-menu) {
  &.is-active {
    > .el-sub-menu__title {
      color: v-bind(activeTextColor);
    }
  }
}

:deep(.el-menu-item.is-active) {
  @extend %tip-line;
}

.el-menu--collapse {
  :deep(.el-sub-menu.is-active) {
    .el-sub-menu__title {
      @extend %tip-line;
      background-color: v-bind(sidebarMenuHoverBgColor);
    }
  }
}

// 底部栏
.sidebar-footer {
  border-top: 1px solid var(--el-border-color-lighter);
  background-color: var(--v3-sidebar-menu-bg-color);
  flex-shrink: 0;
}

.footer-expanded {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  height: 50px;
  box-sizing: border-box;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  overflow: hidden;
}

.user-name {
  font-size: 13px;
  color: var(--v3-sidebar-menu-text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.footer-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50px;
}

.collapse-btn {
  cursor: pointer;
  color: var(--v3-sidebar-menu-text-color);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  &:hover {
    background-color: var(--v3-sidebar-menu-hover-bg-color);
  }
}
</style>
