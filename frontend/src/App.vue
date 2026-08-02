<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="brand">StoneVault 磐石备份中枢</span>
    </el-header>
    <el-main>
      <el-alert
        type="info"
        :closable="false"
        title="项目骨架已就绪"
        description="任务管理、备份日志、文件检索等页面将在后续阶段实现。"
      />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color-light);
}
.brand {
  font-size: 18px;
  font-weight: 600;
}
</style>
