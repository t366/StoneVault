<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="login-title">StoneVault 磐石备份中枢</h2>
      <p class="login-sub">管理员登录</p>
      <el-form :model="form" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入管理员账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="onSubmit">
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import client from '../api'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入管理员账号与密码')
    return
  }
  loading.value = true
  try {
    const data = await client.post('/auth/login', form)
    localStorage.setItem('sv_token', data.token)
    ElMessage.success('登录成功')
    router.push('/tasks')
  } catch (err) {
    ElMessage.error('登录失败，请检查账号与密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #1f2d3d 0%, #2c3e50 100%);
}
.login-card {
  width: 360px;
  padding: 8px 12px;
}
.login-title {
  margin: 0 0 4px;
  text-align: center;
  font-size: 20px;
}
.login-sub {
  margin: 0 0 16px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
.login-btn {
  width: 100%;
}
</style>
