<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete,
  Download,
  EditPen,
  Files,
  Plus,
  Refresh,
  UploadFilled,
  WarningFilled,
} from '@element-plus/icons-vue'

import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteKnowledgeBaseMaterial,
  listKnowledgeBaseMaterials,
  listKnowledgeBases,
  retryKnowledgeBaseMaterial,
  updateKnowledgeBase,
  uploadKnowledgeBaseMaterial,
} from '@/api/knowledgeBase'
import { downloadMaterial } from '@/api/material'
import { formatDateTime } from '@/utils/format'
import {
  fileTypeLabel,
  formatFileSize,
  indexStatusLabel,
  indexStatusType,
} from '@/utils/material'

const loadingKbs = ref(false)
const kbs = ref([])
const selectedId = ref(null)
const materialsLoading = ref(false)
const materials = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const createVisible = ref(false)
const kbMode = ref('create')
const savingKb = ref(false)
const editingKb = ref(null)
const kbForm = reactive({ name: '', description: '' })

const uploadVisible = ref(false)
const uploading = ref(false)
const fileList = ref([])
const uploadTitle = ref('')

let pollTimer = null

const selectedKb = computed(() =>
  kbs.value.find((item) => item.id === selectedId.value),
)
const needsPolling = computed(() =>
  materials.value.some((item) => ['pending', 'indexing'].includes(item.index_status)),
)

function syncPolling() {
  if (needsPolling.value && !pollTimer) {
    pollTimer = setInterval(() => loadMaterials(true), 4000)
  } else if (!needsPolling.value && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
    refreshKbCounts()
  }
}

async function refreshKbCounts() {
  try {
    const body = await listKnowledgeBases()
    kbs.value = body?.data?.items || []
  } catch {
    // Counts are informational; keep the current list on failure.
  }
}

async function loadKbs() {
  loadingKbs.value = true
  try {
    const body = await listKnowledgeBases()
    kbs.value = body?.data?.items || []
    if (!kbs.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = kbs.value[0]?.id ?? null
    }
  } catch (error) {
    ElMessage.error(error?.message || '加载个人知识库失败')
  } finally {
    loadingKbs.value = false
  }
  await loadMaterials()
}

async function selectKb(kb) {
  selectedId.value = kb.id
  page.value = 1
  await loadMaterials()
}

async function loadMaterials(silent = false) {
  if (!selectedId.value) {
    materials.value = []
    total.value = 0
    return
  }
  if (!silent) materialsLoading.value = true
  try {
    const body = await listKnowledgeBaseMaterials(selectedId.value, {
      page: page.value,
      page_size: pageSize.value,
    })
    materials.value = body?.data?.items || []
    total.value = body?.data?.total || 0
    syncPolling()
  } catch (error) {
    if (!silent) ElMessage.error(error?.message || '加载知识库资料失败')
  } finally {
    if (!silent) materialsLoading.value = false
  }
}

function openCreate() {
  kbMode.value = 'create'
  editingKb.value = null
  Object.assign(kbForm, { name: '', description: '' })
  createVisible.value = true
}

function openEdit(kb) {
  kbMode.value = 'edit'
  editingKb.value = kb
  Object.assign(kbForm, { name: kb.name, description: kb.description || '' })
  createVisible.value = true
}

async function saveKb() {
  const name = kbForm.name.trim()
  if (name.length < 2) {
    ElMessage.warning('知识库名称至少 2 个字符')
    return
  }
  savingKb.value = true
  try {
    if (kbMode.value === 'create') {
      const body = await createKnowledgeBase({
        name,
        description: kbForm.description.trim() || null,
      })
      selectedId.value = body.data.id
      ElMessage.success('知识库已创建')
      page.value = 1
    } else {
      await updateKnowledgeBase(editingKb.value.id, {
        name,
        description: kbForm.description.trim() || null,
      })
      ElMessage.success('知识库已更新')
    }
    createVisible.value = false
    await loadKbs()
  } catch (error) {
    ElMessage.error(error?.message || '保存知识库失败')
  } finally {
    savingKb.value = false
  }
}

async function removeKb(kb) {
  if (kb.is_default) {
    ElMessage.warning('默认知识库不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除知识库「${kb.name}」吗？其中的个人资料将不再可访问，并同步清理 RAG 向量。`,
      '删除知识库',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('知识库已删除')
    if (selectedId.value === kb.id) selectedId.value = null
    await loadKbs()
  } catch (error) {
    ElMessage.error(error?.message || '删除知识库失败')
  }
}

function openUpload() {
  fileList.value = []
  uploadTitle.value = ''
  uploadVisible.value = true
}

function onFileChange(uploadFile) {
  if (!uploadTitle.value && uploadFile?.name) {
    uploadTitle.value = uploadFile.name.replace(/\.[^.]+$/, '')
  }
}

async function submitUpload() {
  const file = fileList.value[0]?.raw
  if (!file) {
    ElMessage.warning('请选择要上传的资料文件')
    return
  }
  uploading.value = true
  try {
    await uploadKnowledgeBaseMaterial(selectedId.value, file, {
      title: uploadTitle.value.trim(),
    })
    ElMessage.success('资料已上传，正在后台索引')
    uploadVisible.value = false
    page.value = 1
    await loadMaterials()
    await refreshKbCounts()
  } catch (error) {
    ElMessage.error(error?.message || '上传资料失败')
  } finally {
    uploading.value = false
  }
}

async function download(row) {
  try {
    const blob = await downloadMaterial(row.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = row.source_filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
    row.download_count += 1
  } catch (error) {
    ElMessage.error(error?.message || '下载资料失败')
  }
}

async function retry(row) {
  try {
    await retryKnowledgeBaseMaterial(selectedId.value, row.id)
    ElMessage.success('已重新提交索引')
    await loadMaterials(true)
  } catch (error) {
    ElMessage.error(error?.message || '重试索引失败')
  }
}

async function removeMaterial(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除资料「${row.title}」吗？删除后无法再访问，并同步清理 RAG 向量。`,
      '删除资料',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteKnowledgeBaseMaterial(selectedId.value, row.id)
    ElMessage.success('资料已删除')
    await loadMaterials()
    await refreshKbCounts()
  } catch (error) {
    ElMessage.error(error?.message || '删除资料失败')
  }
}

onMounted(loadKbs)

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="em-page knowledge-bases">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">PERSONAL KNOWLEDGE</span>
        <h1>我的知识库</h1>
        <p>建立自己的学习资料库，上传后直接索引，仅自己可见。</p>
      </div>
      <el-button type="primary" size="large" :icon="Plus" @click="openCreate">
        创建知识库
      </el-button>
    </div>

    <div v-loading="loadingKbs" class="kb-layout">
      <aside class="kb-list">
        <article
          v-for="kb in kbs"
          :key="kb.id"
          class="kb-card em-card"
          :class="{ 'is-active': kb.id === selectedId }"
          @click="selectKb(kb)"
        >
          <div class="kb-card-head">
            <span class="kb-icon"><el-icon><Files /></el-icon></span>
            <el-tag v-if="kb.is_default" type="primary" effect="light" size="small">
              默认
            </el-tag>
          </div>
          <strong>{{ kb.name }}</strong>
          <p>{{ kb.description || '暂无说明' }}</p>
          <div class="kb-counts">
            <span>{{ kb.material_count }} 份资料</span>
            <span>{{ kb.indexed_count }} 已索引</span>
          </div>
          <div class="kb-actions" @click.stop>
            <el-button link type="primary" :icon="EditPen" @click="openEdit(kb)">
              重命名
            </el-button>
            <el-button
              link
              type="danger"
              :icon="Delete"
              :disabled="kb.is_default"
              @click="removeKb(kb)"
            >
              删除
            </el-button>
          </div>
        </article>
      </aside>

      <section class="kb-detail em-card">
        <template v-if="selectedKb">
          <div class="detail-head">
            <div>
              <div class="detail-title">
                <h2>{{ selectedKb.name }}</h2>
                <el-tag v-if="selectedKb.is_default" type="primary" effect="light" size="small">
                  默认知识库
                </el-tag>
              </div>
              <p>{{ selectedKb.description || '暂无说明' }}</p>
              <div class="detail-meta">
                <span>{{ selectedKb.material_count }} 份资料</span>
                <span>{{ selectedKb.indexed_count }} 份已索引</span>
              </div>
            </div>
            <el-button type="primary" :icon="Plus" @click="openUpload">
              上传资料
            </el-button>
          </div>

          <el-table v-loading="materialsLoading" :data="materials" class="material-table">
            <el-table-column label="资料" min-width="240">
              <template #default="{ row }">
                <div class="material-cell">
                  <span class="file-badge">{{ fileTypeLabel(row.file_type) }}</span>
                  <div>
                    <strong>{{ row.title }}</strong>
                    <small>{{ row.source_filename }}</small>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="类型 / 大小" width="130">
              <template #default="{ row }">
                {{ fileTypeLabel(row.file_type) }} · {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column label="索引状态" width="120">
              <template #default="{ row }">
                <div class="index-cell">
                  <el-tag :type="indexStatusType(row.index_status)" effect="plain">
                    {{ indexStatusLabel(row.index_status) }}
                  </el-tag>
                  <el-tooltip v-if="row.index_error" :content="row.index_error" placement="top">
                    <el-icon class="error-icon"><WarningFilled /></el-icon>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="上传时间" width="165">
              <template #default="{ row }">
                <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button link type="primary" :icon="Download" @click="download(row)">
                    下载
                  </el-button>
                  <el-button
                    v-if="row.index_status === 'failed'"
                    link
                    type="warning"
                    :icon="Refresh"
                    @click="retry(row)"
                  >
                    重试
                  </el-button>
                  <el-button link type="danger" :icon="Delete" @click="removeMaterial(row)">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <template #empty>
              <div class="empty-state">
                <div class="empty-icon"><el-icon><Files /></el-icon></div>
                <h3>知识库还没有资料</h3>
                <p>上传自己的学习资料，系统会自动建立索引，供 AI 学伴问答使用。</p>
                <el-button type="primary" :icon="Plus" @click="openUpload">
                  上传第一份资料
                </el-button>
              </div>
            </template>
          </el-table>

          <div v-if="total > pageSize" class="table-footer">
            <el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next"
              @current-change="loadMaterials()"
            />
          </div>
        </template>

        <el-empty v-else description="请选择或创建一个知识库" :image-size="90" />
      </section>
    </div>

    <el-dialog
      v-model="createVisible"
      :title="kbMode === 'create' ? '创建知识库' : '编辑知识库'"
      width="500px"
    >
      <el-form label-position="top">
        <el-form-item label="知识库名称" required>
          <el-input v-model="kbForm.name" placeholder="例如：考研数学、算法笔记" maxlength="100" />
        </el-form-item>
        <el-form-item label="说明（选填）">
          <el-input
            v-model="kbForm.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingKb" @click="saveKb">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="uploadVisible" title="上传个人资料" width="540px">
      <el-form label-position="top">
        <el-form-item label="资料标题">
          <el-input v-model="uploadTitle" placeholder="默认使用文件名" maxlength="200" />
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            v-model:file-list="fileList"
            drag
            class="uploader"
            accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg"
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到这里，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF / DOCX / PPTX / PNG / JPG / JPEG，单个文件不超过 200MB。
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <p class="dialog-hint">
        个人资料仅自己可见，无需管理员审核；上传后直接索引到「{{ selectedKb?.name }}」对应的知识库分组。
      </p>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          上传并索引
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.knowledge-bases {
  display: grid;
  gap: 18px;
}

.kb-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
  min-height: 360px;
}

.kb-list {
  display: grid;
  gap: 12px;
}

.kb-card {
  padding: 16px 18px;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.kb-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 34px rgba(31, 45, 61, 0.09);
}

.kb-card.is-active {
  border-color: #b9d4ff;
  background: linear-gradient(135deg, #ffffff, #f3f9ff);
  box-shadow: 0 14px 34px rgba(22, 119, 255, 0.12);
}

.kb-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.kb-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 11px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 18px;
}

.kb-card strong {
  font-size: 15px;
}

.kb-card p {
  display: -webkit-box;
  min-height: 34px;
  margin-top: 4px;
  overflow: hidden;
  color: var(--em-text-secondary);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.kb-counts {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.kb-actions {
  display: flex;
  gap: 4px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--em-border);
}

.kb-detail {
  padding: 22px 24px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-title h2 {
  font-size: 20px;
}

.detail-head p {
  margin-top: 4px;
  color: var(--em-text-secondary);
  font-size: 13px;
}

.detail-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.material-table {
  width: 100%;
}

.material-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-badge {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 10px;
  font-weight: 700;
}

.material-cell div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.35;
}

.material-cell strong {
  font-size: 14px;
}

.material-cell small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.index-cell {
  display: flex;
  align-items: center;
  gap: 5px;
}

.error-icon {
  color: var(--em-danger);
  cursor: help;
}

.time-text {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 18px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 26px;
}

.empty-state h3 {
  margin-top: 14px;
  font-size: 17px;
}

.empty-state p {
  margin: 4px 0 16px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
}

.uploader {
  width: 100%;
}

.upload-icon {
  color: var(--em-primary);
  font-size: 42px;
}

.dialog-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

@media (max-width: 1024px) {
  .kb-layout {
    grid-template-columns: 1fr;
  }

  .kb-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .kb-list {
    grid-template-columns: 1fr;
  }

  .detail-head {
    flex-direction: column;
  }
}
</style>
