<script lang="ts" setup>
import logoText1 from "@@/assets/images/layouts/logo-text-1.png?url"
import logoText2 from "@@/assets/images/layouts/logo-text-2.png?url"
import logo from "@@/assets/images/layouts/logo.png?url"
import { useLayoutMode } from "@@/composables/useLayoutMode"

interface Props {
  collapse?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapse: true
})

const { isLeft, isTop } = useLayoutMode()
</script>

<template>
  <div class="layout-logo-container" :class="{ 'collapse': props.collapse, 'layout-mode-top': isTop }">
    <transition name="layout-logo-fade">
      <router-link v-if="props.collapse" key="collapse" to="/">
        <img :src="logo" class="layout-logo">
      </router-link>
      <router-link v-else key="expand" to="/">
        <img :src="!isLeft ? logoText2 : logoText1" class="layout-logo-text">
      </router-link>
    </transition>
  </div>
</template>

<style lang="scss" scoped>
.layout-logo-container {
  position: relative;
  width: 100%;
  height: var(--v3-header-height);
  line-height: var(--v3-header-height);
  text-align: center;
  overflow: hidden;
  .layout-logo {
    display: none;
  }
  .layout-logo-text {
    max-height: 80%;
    max-width: 80%;
    vertical-align: middle;
    object-fit: contain;
  }
}

.layout-mode-top {
  height: var(--v3-navigationbar-height);
  line-height: var(--v3-navigationbar-height);
}

.collapse {
  .layout-logo {
    max-width: 80%;
    max-height: 32px;
    vertical-align: middle;
    display: inline-block;
    object-fit: contain;
  }
  .layout-logo-text {
    display: none;
  }
}
</style>
