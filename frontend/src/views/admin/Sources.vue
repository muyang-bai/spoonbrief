<script setup>
import SmartSelect from '../../components/SmartSelect.vue'
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import { confirmDialog } from '../../confirm'
import Modal from '../../components/Modal.vue'

const sources = ref([])
const loading = ref(true)
const showModal = ref(false)
const editing = ref(null)
const form = ref(blankForm())
const saving = ref(false)
const toggling = ref(null)

const sourceTypes = [
  { v: 'rss', label: 'RSS' },
  { v: 'dailyhot', label: '每日热点' },
  { v: 'newsapi', label: 'NewsAPI' },
  { v: 'bing_news', label: 'Bing News' },
]
const typeBadge = {
  rss: 'badge-teal',
  dailyhot: 'badge',
  newsapi: 'badge-blue',
  bing_news: 'badge-green',
}
const categories = ['综合', '科技', '财经', '国际', '时政', '社会', '娱乐', '体育', '自定义']

function blankForm() {
  return {
    name: '',
    source_type: 'rss',
    source_category: '综合',
    url: '',
    api_key_ref: '',
    fetch_interval: 60,
    credibility: 5,
    description: '',
  }
}

function typeLabel(v) {
  return sourceTypes.find((s) => s.v === v)?.label || v || '—'
}

function remainingLabel(s) {
  if (s.api_remaining_label) return s.api_remaining_label
  if (s.api_remaining == null || s.api_remaining === '') return '—'
  const n = Number(s.api_remaining)
  if (!Number.isFinite(n)) return '—'
  if (n < 0) return '不限'
  return String(n)
}


async function load() {
  loading.value = true
  try {
    sources.value = await api('/admin/sources')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = blankForm()
  showModal.value = true
}

function openEdit(s) {
  editing.value = s
  form.value = {
    name: s.name || '',
    source_type: s.source_type || 'rss',
    source_category: s.source_category || '综合',
    url: s.url || '',
    api_key_ref: s.api_key_ref || '',
    fetch_interval: s.fetch_interval ?? 60,
    credibility: s.credibility ?? 5,
    description: s.description || '',
  }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return t.err('请输入信息源名称')
  if (form.value.source_type !== 'dailyhot' && !form.value.url.trim()) return t.err('请填写 URL')
  const body = { ...form.value }
  if (!body.api_key_ref) delete body.api_key_ref
  saving.value = true
  try {
    if (editing.value) {
      await api(`/sources/${editing.value.id}`, { method: 'PUT', body })
      t.ok('信息源已更新')
    } else {
      await api('/sources/', { method: 'POST', body })
      t.ok('信息源已添加')
    }
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(s) {
  if (!(await confirmDialog({ text: `确认删除信息源「${s.name}」吗？` }))) return
  try {
    await api(`/sources/${s.id}`, { method: 'DELETE' })
    t.ok('信息源已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

async function toggleActive(s, checked) {
  toggling.value = s.id
  try {
    await api(`/sources/${s.id}`, { method: 'PUT', body: { is_active: checked } })
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    toggling.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">管理平台聚合的信息源</p>
      <button class="btn btn-primary" @click="openCreate">＋ 添加信息源</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="sources.length === 0" class="card empty">
      <div class="big">🛰️</div>
      <p>暂未添加信息源</p>
      <p class="muted" style="margin: 8px 0 16px">添加信息源后，系统将按设定间隔抓取热点</p>
      <button class="btn btn-primary" @click="openCreate">添加第一个信息源</button>
    </div>

    <div v-else class="card" style="padding: 8px 12px">
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>类别</th>
            <th>可信度</th>
            <th>状态</th>
            <th>剩余调用</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sources" :key="s.id">
            <td>
              <div>{{ s.name }}</div>
              <div class="faint" style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                {{ s.url || '—' }}
              </div>
            </td>
            <td>
              <span class="badge" :class="typeBadge[s.source_type] || 'badge-gray'">{{ typeLabel(s.source_type) }}</span>
            </td>
            <td>{{ s.source_category || '—' }}</td>
            <td>{{ s.credibility ?? '—' }}</td>
            <td>
              <div style="display: flex; align-items: center; gap: 8px">
                <span v-if="s.is_active" class="badge badge-green">启用</span>
                <span v-else class="badge badge-gray">停用</span>
                <label class="chip" style="cursor: pointer">
                  <input type="checkbox" :checked="!!s.is_active" :disabled="toggling === s.id" style="accent-color: var(--primary)" @change="toggleActive(s, $event.target.checked)" />
                  启用
                </label>
              </div>
            </td>
            <td>{{ remainingLabel(s) }}</td>
            <td>
              <div style="display: flex; gap: 6px">
                <button class="btn btn-outline btn-sm" @click="openEdit(s)">编辑</button>
                <button class="btn btn-sm" style="color: var(--danger)" @click="remove(s)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showModal" :title="editing ? '编辑信息源' : '添加信息源'" @close="showModal = false">
      <label class="field">
        <span>名称</span>
        <input v-model="form.name" class="input" placeholder="例如：36氪 RSS" />
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>类型</span>
          <SmartSelect v-model="form.source_type" :options="sourceTypes.map(s => ({value:s.v,label:s.label}))" label="信源类型" />
        </label>
        <label class="field">
          <span>类别</span>
          <SmartSelect v-model="form.source_category" :options="categories.map(c => ({value:c,label:c}))" label="分类" />
        </label>
      </div>
      <label class="field">
        <span>URL</span>
        <input v-model="form.url" class="input" placeholder="https://…" :disabled="form.source_type === 'dailyhot'" />
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>API Key 引用</span>
          <input v-model="form.api_key_ref" class="input" placeholder="可选，如 newsapi_key" />
        </label>
        <label class="field">
          <span>抓取间隔（分钟）</span>
          <input v-model.number="form.fetch_interval" type="number" min="1" class="input" placeholder="60" />
        </label>
      </div>
      <label class="field">
        <span>可信度（1-10）</span>
        <input v-model.number="form.credibility" type="number" min="1" max="10" class="input" placeholder="5" />
      </label>
      <label class="field">
        <span>描述</span>
        <textarea v-model="form.description" class="textarea" placeholder="选填，简要说明该信息源" style="min-height: 64px"></textarea>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> {{ editing ? '保存修改' : '添加' }}
        </button>
      </div>
    </Modal>
  </div>
</template>
