<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="任务名称" min-width="140" />
      <el-table-column prop="source_path" label="源目录" min-width="180" show-overflow-tooltip />
      <el-table-column prop="hdd_rel_path" label="冷区路径" min-width="120" />
      <el-table-column prop="schedule_cron" label="调度(Cron)" width="130">
        <template #default="{ row }">
          <span v-if="row.schedule_cron">{{ row.schedule_cron }}</span>
          <el-tag v-else type="info" size="small">仅手动</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="backup_mode" label="模式" width="100">
        <template #default="{ row }">
          <el-tag :type="row.backup_mode === 'incremental' ? 'success' : 'warning'" size="small">
            {{ row.backup_mode === 'incremental' ? '增量' : '全量' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="runTask(row)">运行</el-button>
          <el-button size="small" link @click="openLogs(row)">日志</el-button>
          <el-button size="small" link @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="removeTask(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑任务' : '新建任务'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="form" label-width="140px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="例如：手机相册备份" />
        </el-form-item>
        <el-form-item label="源目录" required>
          <el-input v-model="form.source_path" placeholder="终端上的源目录绝对路径" />
        </el-form-item>
        <el-form-item label="冷区目标相对路径" required>
          <el-input v-model="form.hdd_rel_path" placeholder="冷区下的相对路径，如 photos" />
        </el-form-item>
        <el-form-item label="调度规则(Cron)">
          <el-input v-model="form.schedule_cron" placeholder="留空表示仅手动触发，如 0 2 * * *" />
        </el-form-item>
        <el-form-item label="备份模式">
          <el-radio-group v-model="form.backup_mode">
            <el-radio value="full">全量</el-radio>
            <el-radio value="incremental">增量</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="扩展名过滤">
          <el-select
            v-model="form.filter_extensions"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="按扩展名白名单过滤，留空不过滤"
          />
        </el-form-item>
        <el-form-item label="大小过滤(B)">
          <el-input-number v-model="form.filter_min_size" :min="0" placeholder="下限" />
          <span class="gap">~</span>
          <el-input-number v-model="form.filter_max_size" :min="0" placeholder="上限" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import client from '../api'

const router = useRouter()
const items = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)

function emptyForm() {
  return {
    id: null,
    name: '',
    source_path: '',
    hdd_rel_path: '',
    schedule_cron: '',
    backup_mode: 'full',
    filter_extensions: [],
    filter_min_size: null,
    filter_max_size: null,
    enabled: true,
  }
}
const form = reactive(emptyForm())

async function load() {
  loading.value = true
  try {
    const data = await client.get('/tasks/')
    items.value = data.items
  } catch (err) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name,
    source_path: row.source_path,
    hdd_rel_path: row.hdd_rel_path,
    schedule_cron: row.schedule_cron || '',
    backup_mode: row.backup_mode,
    filter_extensions: row.filter_extensions || [],
    filter_min_size: row.filter_min_size ?? null,
    filter_max_size: row.filter_max_size ?? null,
    enabled: !!row.enabled,
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name || !form.source_path || !form.hdd_rel_path) {
    ElMessage.warning('任务名称、源目录与冷区路径为必填项')
    return
  }
  saving.value = true
  const payload = { ...form }
  delete payload.id
  try {
    if (form.id) {
      await client.put(`/tasks/${form.id}`, payload)
      ElMessage.success('任务已更新')
    } else {
      await client.post('/tasks/', payload)
      ElMessage.success('任务已创建')
    }
    dialogVisible.value = false
    load()
  } catch (err) {
    const msg = err.response?.data?.error || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function runTask(row) {
  try {
    const data = await client.post(`/tasks/${row.id}/run`)
    if (data.triggered) {
      ElMessage.success(`任务「${row.name}」已触发执行`)
    } else {
      ElMessage.info(data.reason || '任务正在运行，本次触发已合并')
    }
  } catch (err) {
    ElMessage.error('触发失败')
  }
}

async function removeTask(row) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${row.name}」？`, '提示', { type: 'warning' })
    await client.delete(`/tasks/${row.id}`)
    ElMessage.success('任务已删除')
    load()
  } catch (err) {
    /* 取消或失败 */
  }
}

function openLogs(row) {
  router.push(`/tasks/${row.id}/logs`)
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  margin-bottom: 14px;
}
.gap {
  margin: 0 8px;
  color: #909399;
}
</style>
