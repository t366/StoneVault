<template>
  <div class="page">
    <div class="toolbar">
      <el-button :icon="Back" @click="router.back()">返回</el-button>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="快照ID" width="90" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="开始时间" min-width="170" />
      <el-table-column prop="finished_at" label="结束时间" min-width="170">
        <template #default="{ row }">{{ row.finished_at || '—' }}</template>
      </el-table-column>
      <el-table-column prop="file_count" label="文件数" width="90" />
      <el-table-column prop="total_bytes" label="数据量" width="110">
        <template #default="{ row }">{{ formatBytes(row.total_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="error_message" label="错误信息" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.error_message" class="err-text">{{ row.error_message }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Refresh } from '@element-plus/icons-vue'
import client from '../api'

const route = useRoute()
const router = useRouter()
const items = ref([])
const loading = ref(false)

function statusText(status) {
  return {
    pending: '等待',
    running: '执行中',
    success: '成功',
    failed: '失败',
    skipped: '跳过',
  }[status] || status
}

function statusType(status) {
  return {
    pending: 'info',
    running: 'primary',
    success: 'success',
    failed: 'danger',
    skipped: 'warning',
  }[status] || 'info'
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = bytes
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`
}

async function load() {
  loading.value = true
  try {
    const data = await client.get(`/tasks/${route.params.id}/logs`)
    items.value = data.items
  } catch (err) {
    ElMessage.error('加载任务日志失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  margin-bottom: 14px;
}
.err-text {
  color: #f56c6c;
}
</style>
