<template>
  <div class="page">
    <el-form inline class="filter-form" @submit.prevent="load">
      <el-form-item label="文件名">
        <el-input v-model="filters.q" placeholder="模糊匹配文件名" clearable @keyup.enter="load" />
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input v-model="filters.ext" placeholder="如 jpg / .pdf" clearable @keyup.enter="load" />
      </el-form-item>
      <el-form-item label="备份时间">
        <el-date-picker
          v-model="timeRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          clearable
        />
      </el-form-item>
      <el-form-item label="大小(B)">
        <el-input-number v-model="filters.size_min" :min="0" placeholder="下限" controls-position="right" />
        <span class="gap">~</span>
        <el-input-number v-model="filters.size_max" :min="0" placeholder="上限" controls-position="right" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="filename" label="文件名" min-width="160" show-overflow-tooltip />
      <el-table-column prop="rel_path" label="相对路径" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_size" label="大小" width="110">
        <template #default="{ row }">{{ formatBytes(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="backup_time" label="备份时间" min-width="170" />
      <el-table-column prop="content_type" label="类型" min-width="140">
        <template #default="{ row }">{{ row.content_type || '—' }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next, sizes"
      :total="total"
      :current-page="page"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pageSize"
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import client from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const timeRange = ref(null)

const filters = reactive({
  q: '',
  ext: '',
  size_min: null,
  size_max: null,
})

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
    const params = {
      page: page.value,
      page_size: pageSize.value,
      q: filters.q || undefined,
      ext: filters.ext || undefined,
      size_min: filters.size_min ?? undefined,
      size_max: filters.size_max ?? undefined,
    }
    if (timeRange.value && timeRange.value.length === 2) {
      params.from = timeRange.value[0]
      params.to = timeRange.value[1]
    }
    const data = await client.get('/files/', { params })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.q = ''
  filters.ext = ''
  filters.size_min = null
  filters.size_max = null
  timeRange.value = null
  page.value = 1
  load()
}

function onPageChange(p) {
  page.value = p
  load()
}

function onSizeChange(s) {
  pageSize.value = s
  page.value = 1
  load()
}

onMounted(load)
</script>

<style scoped>
.filter-form {
  margin-bottom: 8px;
}
.filter-form :deep(.el-form-item) {
  margin-bottom: 12px;
}
.gap {
  margin: 0 8px;
  color: #909399;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
