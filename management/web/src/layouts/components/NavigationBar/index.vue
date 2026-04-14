<script lang="ts" setup>
import { useLayoutMode } from "@@/composables/useLayoutMode"
import { Breadcrumb, Sidebar } from "../index"
import { useDevice } from "@@/composables/useDevice"

const { isMobile } = useDevice()
const { isTop } = useLayoutMode()
</script>

<template>
  <div class="navigation-bar">
    <Breadcrumb v-if="!isTop || isMobile" class="breadcrumb" />
    <Sidebar v-if="isTop && !isMobile" class="sidebar" />
  </div>
</template>

<style lang="scss" scoped>
.navigation-bar {
  height: var(--v3-navigationbar-height);
  overflow: hidden;
  color: var(--v3-navigationbar-text-color);
  display: flex;
  align-items: center;
  .breadcrumb {
    flex: 1;
    @media screen and (max-width: 576px) {
      display: none;
    }
  }
  .sidebar {
    flex: 1;
    min-width: 0px;
    :deep(.el-menu) {
      background-color: transparent;
    }
    :deep(.el-sub-menu) {
      &.is-active {
        .el-sub-menu__title {
          color: var(--el-color-primary);
        }
      }
    }
  }
}
</style>
