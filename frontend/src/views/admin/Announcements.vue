<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import { confirmDialog } from '../../confirm'
import Modal from '../../components/Modal.vue'

const list = ref([])
const loading = ref(true)
const showModal = ref(false)
const form = ref(blankForm())
const saving = ref(false)
const erasing = ref(null)

function blankForm() {
  return {
    title: '',
    body: '',
    is_pinned: false,
  }
}

async function load() {
  loading.value = true
  try {
    list.value = await api('/admin/announcements')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = blankForm()
  showModal.value = true
}

async function save() {
  if (!form.value.title.trim()) return t.err('请输入公告标题')
  if (!form.value.body.trim()) return t.err('请输入公告正文')
  saving.value = true
  try {
    await api('/announcements/', { method: 'POST', body: form.value })
    t.ok('公告已发布')
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function erase(a) {
  if (!(await confirmDialog({ text: `确认擦除公告「${a.title}」吗？擦除后用户端不再展示。` }))) return
  erasing.value = a.id
  try {
    await api(`/announcements/${a.id}/erase`, { method: 'PUT' })
    t.ok('公告已擦除')
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    erasing.value = null
  }
}

async function remove(a) {
  if (!(await confirmDialog({ text: '确认删除此公告？' }))) return
  try {
    await api(`/announcements/${a.id}`, { method: 'DELETE' })
    t.ok('公告已删除')
    await load()
  } catch (e) {
    t.err(e.message)
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
      <p class="muted">发布站内公告，用户端首页展示</p>
      <button class="btn btn-primary" @click="openCreate">＋ 发布公告</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="list.length === 0" class="card empty">
      <div class="big">📢</div>
      <p>暂无公告</p>
      <p class="muted" style="margin: 8px 0 16px">发布第一条公告，向用户传达重要信息</p>
      <button class="btn btn-primary" @click="openCreate">发布公告</button>
    </div>

    <div v-else class="card" style="padding: 8px 12px">
      <table class="table">
        <thead>
          <tr>
            <th>标题</th>
            <th>置顶</th>
            <th>状态</th>
            <th>发布时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in list" :key="a.id">
            <td>
              <div>{{ a.title }}</div>
              <div class="faint" style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                {{ a.body || '—' }}
              </div>
            </td>
            <td>
              <span v-if="a.is_pinned" class="badge">置顶</span>
              <span v-else class="faint">—</span>
            </td>
            <td>
              <span v-if="a.erased_at" class="badge badge-red">已擦除</span>
              <span v-else class="badge badge-green">展示中</span>
            </td>
            <td class="muted">{{ fmtTime(a.published_at) }}</td>
            <td>
              <div style="display: flex; gap: 6px">
                <button v-if="!a.erased_at" class="btn btn-outline btn-sm" :disabled="erasing === a.id" @click="erase(a)">
                  <span v-if="erasing === a.id" class="spinner spinner-dark"></span> 擦除
                </button>
                <button class="btn btn-sm" style="color: var(--danger)" @click="remove(a)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showModal" title="发布公告" @close="showModal = false">
      <label class="field">
        <span>标题</span>
        <input v-model="form.title" class="input" placeholder="例如：系统维护通知" />
      </label>
      <label class="field">
        <span>正文</span>
        <textarea v-model="form.body" class="textarea" placeholder="公告内容…"></textarea>
      </label>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="form.is_pinned" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">置顶展示</span>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> 发布
        </button>
      </div>
    </Modal>
  </div>
</template>
