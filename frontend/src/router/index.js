import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'

const routes = [
  { path: '/login', name: 'login', component: Login },
  { path: '/', redirect: '/tasks' },
  {
    path: '/tasks',
    name: 'tasks',
    component: () => import('../views/TaskList.vue'),
    meta: { title: '任务管理' },
  },
  {
    path: '/tasks/:id/logs',
    name: 'task-logs',
    component: () => import('../views/TaskLogs.vue'),
    meta: { title: '任务日志' },
  },
  {
    path: '/files',
    name: 'files',
    component: () => import('../views/FileList.vue'),
    meta: { title: '文件检索' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('sv_token')
  if (to.path !== '/login' && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/tasks'
  }
  document.title = to.meta?.title ? `${to.meta.title} - StoneVault` : 'StoneVault'
  return true
})

export default router
