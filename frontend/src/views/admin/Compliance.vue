<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import Modal from '../../components/Modal.vue'

const items = ref([])
const loading = ref(true)
const showModal = ref(false)
const editing = ref(null)
const content = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    items.value = await api('/admin/compliance')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openEdit(item) {
  editing.value = item
  content.value = item.content || ''
  showModal.value = true
}

async function save() {
  if (!content.value.trim()) return t.err('内容不能为空')
  saving.value = true
  try {
    await api('/admin/compliance', {
      method: 'PUT',
      body: { key: editing.value.key, content: content.value },
    })
    t.ok('合规文本已保存')
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">免责声明等合规内容，展示于用户端页脚</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="items.length === 0" class="card empty">
      <div class="big">📜</div>
      <p>暂无合规文本</p>
    </div>

    <div v-else class="grid-2">
      <div v-for="item in items" :key="item.key" class="card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px">
          <h3 style="margin-bottom: 4px">{{ item.title || item.key }}</h3>
          <span class="chip">{{ item.key }}</span>
        </div>
        <p class="muted" style="white-space: pre-wrap; max-height: 96px; overflow: hidden; margin-bottom: 10px">
          {{ item.content || '—' }}
        </p>
        <p class="faint" style="margin-bottom: 12px">最后更新：{{ fmtTime(item.updated_at) }}</p>
        <button class="btn btn-outline btn-sm" @click="openEdit(item)">编辑</button>
      </div>
    </div>

    <Modal :show="showModal" :title="`编辑合规文本${editing ? ' · ' + (editing.title || editing.key) : ''}`" width="680px" @close="showModal = false">
      <label class="field">
        <span>内容</span>
        <textarea v-model="content" class="textarea" style="min-height: 220px" placeholder="请输入合规文本内容…"></textarea>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> 保存
        </button>
      </div>
    </Modal>
  </div>
</template>
