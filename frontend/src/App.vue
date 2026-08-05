<template>
  <router-view v-if="!isAuthed" />
  <el-container v-else class="layout">
    <el-aside width="200px" class="aside">
      <div class="brand">StoneVault</div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </el-menu-item>
        <el-menu-item index="/files">
          <el-icon><Folder /></el-icon>
          <span>文件检索</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ $route.meta?.title || '' }}</span>
        <el-dropdown @command="onCommand">
          <span class="user">
            <el-icon><User /></el-icon>
            <span>管理员</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { List, Folder, User } from '@element-plus/icons-vue'

const router = useRouter()
const isAuthed = computed(() => !!localStorage.getItem('sv_token'))

function onCommand(command) {
  if (command === 'logout') {
    localStorage.removeItem('sv_token')
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.aside {
  background: #1f2d3d;
  color: #fff;
}
.brand {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.menu {
  border-right: none;
  background: transparent;
}
.menu :deep(.el-menu-item) {
  color: #c0c4cc;
}
.menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
}
.page-title {
  font-size: 16px;
  font-weight: 600;
}
.user {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--el-text-color-regular);
}
</style>
