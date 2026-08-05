<template>
  <el-dialog
    :model-value="modelValue"
    :title="file?.filename || '预览'"
    width="820px"
    top="6vh"
    destroy-on-close
    class="preview-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="preview-body">
      <div v-if="kind === 'image'" class="image-wrap">
        <el-switch
          v-model="originalMode"
          active-text="原图"
          inactive-text="缩略图"
          class="mode-switch"
          @change="loadImage"
        />
        <img v-if="imageUrl" :src="imageUrl" class="preview-image" alt="预览图片" />
        <el-empty v-else description="图片加载失败" />
      </div>

      <div v-else-if="kind === 'text'" class="text-wrap">
        <pre v-if="textContent" class="text-content">{{ textContent }}</pre>
        <el-empty v-else description="文本加载失败" />
      </div>

      <div v-else-if="kind === 'pdf'" class="pdf-wrap">
        <div v-for="(url, index) in pageUrls" :key="index" class="pdf-page">
          <img :src="url" :alt="`第 ${index + 1} 页`" />
        </div>
        <el-empty v-if="!loading && pageUrls.length === 0" description="PDF 加载失败" />
      </div>

      <el-empty v-else description="该文件类型暂不支持在线预览" />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import * as pdfjsLib from 'pdfjs-dist'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import client from '../api'

pdfjsLib.GlobalWorkerOptions.workerSrc = PdfWorker

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  file: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const kind = ref('')
const imageUrl = ref('')
const textContent = ref('')
const pageUrls = ref([])
const originalMode = ref(false)

let pdfDoc = null
let objectUrls = []

const kindMap = {
  jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', bmp: 'image', webp: 'image',
  pdf: 'pdf',
  txt: 'text', md: 'text', log: 'text', csv: 'text', json: 'text', xml: 'text',
}

function detectKind() {
  const name = props.file?.filename || ''
  const dot = name.lastIndexOf('.')
  const ext = dot >= 0 ? name.slice(dot + 1).toLowerCase() : ''
  return kindMap[ext] || 'unsupported'
}

function cleanup() {
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }
  objectUrls.forEach((u) => URL.revokeObjectURL(u))
  objectUrls = []
  imageUrl.value = ''
  textContent.value = ''
  pageUrls.value = []
}

async function load() {
  cleanup()
  if (!props.modelValue || !props.file) return
  kind.value = detectKind()
  if (kind.value === 'image') {
    await loadImage()
  } else if (kind.value === 'text') {
    await loadText()
  } else if (kind.value === 'pdf') {
    await loadPdf()
  }
}

async function loadImage() {
  loading.value = true
  try {
    if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
    const mode = originalMode.value ? 'original' : 'thumbnail'
    const blob = await client.get(`/files/${props.file.id}/preview?mode=${mode}`, {
      responseType: 'blob',
    })
    imageUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    imageUrl.value = ''
    ElMessage.error('图片加载失败')
  } finally {
    loading.value = false
  }
}

async function loadText() {
  loading.value = true
  try {
    const data = await client.get(`/files/${props.file.id}/preview`, {
      responseType: 'text',
    })
    textContent.value = data
  } catch (err) {
    textContent.value = ''
    ElMessage.error('文本加载失败')
  } finally {
    loading.value = false
  }
}

async function loadPdf() {
  loading.value = true
  try {
    const blob = await client.get(`/files/${props.file.id}/preview`, {
      responseType: 'blob',
    })
    const buffer = await blob.arrayBuffer()
    pdfDoc = await pdfjsLib.getDocument({ data: buffer }).promise
    const rendered = []
    for (let i = 1; i <= Math.min(pdfDoc.numPages, 50); i += 1) {
      const page = await pdfDoc.getPage(i)
      const viewport = page.getViewport({ scale: 1.4 })
      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise
      const url = canvas.toDataURL('image/jpeg', 0.85)
      rendered.push(url)
    }
    pageUrls.value = rendered
  } catch (err) {
    pageUrls.value = []
    ElMessage.error('PDF 加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.file],
  () => load(),
  { deep: false }
)
</script>

<style scoped>
.preview-body {
  min-height: 320px;
  max-height: 70vh;
  overflow: auto;
}
.image-wrap {
  text-align: center;
}
.mode-switch {
  margin-bottom: 12px;
}
.preview-image {
  max-width: 100%;
}
.text-wrap {
  padding: 4px 8px;
}
.text-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.6;
}
.pdf-page {
  margin-bottom: 10px;
  text-align: center;
}
.pdf-page img {
  max-width: 100%;
  border: 1px solid var(--el-border-color-lighter);
}
</style>
