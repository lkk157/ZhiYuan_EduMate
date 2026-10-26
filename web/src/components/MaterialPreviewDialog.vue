<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Document, Picture } from '@element-plus/icons-vue'

import {
  downloadMaterial,
  markMaterialViewed,
  previewMaterial,
} from '@/api/material'
import { fileTypeLabel, formatFileSize } from '@/utils/material'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  material: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const loading = ref(false)
const error = ref('')
const kind = ref('unsupported')
const objectUrl = ref('')
const docxHost = ref(null)
const pptxHost = ref(null)
let pptxPreviewer = null

const fileSuffix = computed(() => (props.material?.file_type || '').toLowerCase())

function reset() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
  error.value = ''
  kind.value = 'unsupported'
  if (docxHost.value) docxHost.value.innerHTML = ''
  if (pptxHost.value) pptxHost.value.innerHTML = ''
  pptxPreviewer = null
}

async function loadPreview() {
  reset()
  if (!props.material) return
  loading.value = true
  try {
    markMaterialViewed(props.material.id).catch(() => {})
    const blob = await previewMaterial(props.material.id)
    const suffix = fileSuffix.value

    if (suffix === '.pdf') {
      kind.value = 'pdf'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (['.png', '.jpg', '.jpeg'].includes(suffix)) {
      kind.value = 'image'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (suffix === '.docx') {
      kind.value = 'docx'
      await nextTick()
      const { renderAsync } = await import('docx-preview')
      await renderAsync(blob, docxHost.value, null, {
        className: 'docx-preview',
        inWrapper: true,
        ignoreWidth: true,
        breakPages: true,
      })
    } else if (suffix === '.pptx') {
      kind.value = 'pptx'
      await nextTick()
      const { init } = await import('pptx-preview')
      pptxPreviewer = init(pptxHost.value, { width: 900, height: 506 })
      await pptxPreviewer.preview(await blob.arrayBuffer())
    } else {
      kind.value = 'unsupported'
    }
  } catch (err) {
    if (kind.value === 'docx' || kind.value === 'pptx') {
      error.value = '该文档解析失败，请下载后查看。'
    } else {
      error.value = err?.message || '加载预览失败'
    }
  } finally {
    loading.value = false
  }
}

async function downloadOriginal() {
  if (!props.material) return
  try {
    const blob = await downloadMaterial(props.material.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = props.material.source_filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
    props.material.download_count = (props.material.download_count || 0) + 1
  } catch (err) {
    ElMessage.error(err?.message || '下载资料失败')
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) loadPreview()
    else reset()
  },
)

watch(
  () => props.material?.id,
  () => {
    if (props.modelValue) loadPreview()
  },
)
</script>

<template>
  <el-dialog
    v-model="visible"
    width="min(1040px, 94vw)"
    top="5vh"
    destroy-on-close
    class="material-preview-dialog"
    @closed="reset"
  >
    <template #header>
      <div class="preview-title">
        <span class="preview-icon">
          <el-icon><Document /></el-icon>
        </span>
        <div>
          <strong>{{ material?.title || '资料预览' }}</strong>
          <small>
            {{ material?.source_filename }}
            <template v-if="material?.file_size">
              · {{ formatFileSize(material.file_size) }}
            </template>
          </small>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="preview-body">
      <div v-if="error" class="preview-state">
        <h3>预览失败</h3>
        <p>{{ error }}</p>
        <el-button type="primary" plain :icon="Download" @click="downloadOriginal">
          下载后查看
        </el-button>
      </div>

      <div v-else-if="kind === 'pdf'" class="preview-frame-wrap">
        <iframe class="preview-frame" :src="objectUrl" :title="material?.title" />
      </div>

      <div v-else-if="kind === 'image'" class="preview-image-wrap">
        <img class="preview-image" :src="objectUrl" :alt="material?.title" />
      </div>

      <div v-else-if="kind === 'docx'" ref="docxHost" class="preview-docx" />

      <div v-else-if="kind === 'pptx'" ref="pptxHost" class="preview-pptx" />

      <div v-else class="preview-state">
        <div class="state-icon"><el-icon><Picture /></el-icon></div>
        <h3>暂不支持该格式在线预览</h3>
        <p>{{ fileTypeLabel(fileSuffix) }} 文件请下载后使用本地应用查看。</p>
        <el-button type="primary" plain :icon="Download" @click="downloadOriginal">
          下载资料
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="preview-footer">
        <span class="preview-hint">
          预览不会增加下载次数；DOCX / PPTX 为在线解析效果，排版可能与本地软件略有差异。
        </span>
        <el-button type="primary" :icon="Download" @click="downloadOriginal">
          下载原文件
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.preview-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.preview-icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 11px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 19px;
}

.preview-title > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.preview-title strong {
  overflow: hidden;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-title small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-body {
  min-height: 320px;
  max-height: 72vh;
  overflow: auto;
  border: 1px solid var(--em-border);
  border-radius: 12px;
  background: #f5f7fb;
}

.preview-frame-wrap,
.preview-frame {
  width: 100%;
  height: 70vh;
}

.preview-frame {
  border: 0;
  background: #fff;
}

.preview-image-wrap {
  display: grid;
  min-height: 320px;
  place-items: center;
  padding: 20px;
  background: #eef2f8;
}

.preview-image {
  max-width: 100%;
  max-height: 66vh;
  border-radius: 8px;
  box-shadow: 0 8px 28px rgba(31, 45, 61, 0.16);
}

.preview-docx {
  min-height: 320px;
  padding: 12px;
}

.preview-docx :deep(.docx-wrapper) {
  padding: 12px !important;
  background: #eef2f8 !important;
}

.preview-pptx {
  min-height: 320px;
  padding: 12px;
  overflow: auto;
}

.preview-state {
  display: flex;
  min-height: 320px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px;
  text-align: center;
}

.preview-state h3 {
  font-size: 16px;
}

.preview-state p {
  max-width: 480px;
  margin: 6px 0 16px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

.state-icon {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
  border-radius: 16px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 24px;
}

.preview-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-hint {
  color: var(--em-text-muted);
  font-size: 11px;
  text-align: left;
}

@media (max-width: 760px) {
  .preview-frame-wrap,
  .preview-frame {
    height: 65vh;
  }

  .preview-footer {
    justify-content: flex-end;
  }

  .preview-hint {
    width: 100%;
  }
}
</style>
