<script setup>
import SmartSelect from '../../components/SmartSelect.vue'
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import { confirmDialog } from '../../confirm'
import Modal from '../../components/Modal.vue'

const users = ref([])
const loading = ref(true)
const page = ref(1)
const size = 20
const keyword = ref('')

const showEdit = ref(false)
const editingId = ref(null)
const editForm = ref({ nickname: '', role: 'user', is_active: true })
const savingEdit = ref(false)

const showQuota = ref(false)
const quotaUser = ref(null)
const quotaForm = ref({ api_quota_total: 0, api_quota_used: 0 })
const quotaLoading = ref(false)
const savingQuota = ref(false)

async function load() {
  loading.value = true
  try {
    users.value = await api('/admin/users', { params: { page: page.value, size, keyword: keyword.value } })
    if (users.value.length === 0 && page.value > 1) {
      page.value -= 1
      await load()
    }
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function fmt(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

function openEdit(u) {
  editingId.value = u.id
  editForm.value = { nickname: u.nickname || '', role: u.role || 'user', is_active: !!u.is_active }
  showEdit.value = true
}

async function saveEdit() {
  savingEdit.value = true
  try {
    await api(`/admin/users/${editingId.value}`, { method: 'PUT', body: editForm.value })
    t.ok('用户已更新')
    showEdit.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    savingEdit.value = false
  }
}

async function openQuota(u) {
  quotaUser.value = u
  showQuota.value = true
  quotaLoading.value = true
  try {
    const q = await api(`/admin/users/${u.id}/quota`)
    quotaForm.value = { api_quota_total: q.api_quota_total ?? 0, api_quota_used: q.api_quota_used ?? 0 }
  } catch (e) {
    t.err(e.message)
  } finally {
    quotaLoading.value = false
  }
}

async function saveQuota() {
  if (!Number.isFinite(quotaForm.value.api_quota_total) || !Number.isFinite(quotaForm.value.api_quota_used)) {
    return t.err('请填写有效的配额数值')
  }
  if (quotaForm.value.api_quota_used > quotaForm.value.api_quota_total) {
    return t.err('已用次数不能大于配额总量')
  }
  savingQuota.value = true
  try {
    await api(`/admin/users/${quotaUser.value.id}/quota`, {
      method: 'PUT',
      body: {
        api_quota_total: Number(quotaForm.value.api_quota_total),
        api_quota_used: Number(quotaForm.value.api_quota_used),
      },
    })
    t.ok('配额已更新')
    showQuota.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    savingQuota.value = false
  }
}

async function remove(u) {
  if (!(await confirmDialog({ text: `确定删除用户「${u.email}」吗？删除后不可恢复` }))) return
  try {
    await api(`/admin/users/${u.id}`, { method: 'DELETE' })
    t.ok('用户已删除')
    if (users.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <div class="toolbar">
        <input v-model="keyword" class="input" style="width: 260px" placeholder="搜索邮箱或昵称" @keyup.enter="search" />
        <button class="btn btn-outline" :disabled="loading" @click="search">搜索</button>
      </div>
      <p class="muted">第 {{ page }} 页 · 每页 {{ size }} 条</p>
    </div>

    <div class="card" style="padding: 8px 0">
      <div v-if="loading" class="loading-center">加载中…</div>

      <div v-else-if="users.length === 0" class="empty">
        <div class="big">👥</div>
        <p>{{ keyword ? '未找到用户' : '暂无用户' }}</p>
      </div>

      <div v-else style="overflow-x: auto">
        <table class="table">
          <thead>
            <tr>
              <th>邮箱</th>
              <th>昵称</th>
              <th>权限</th>
              <th>会员档位</th>
              <th>订阅数</th>
              <th>配额</th>
              <th>状态</th>
              <th>注册时间</th>
              <th style="text-align: right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.email }}</td>
              <td>{{ u.nickname || '—' }}</td>
              <td>
                <span class="badge" :class="(u.permission || u.role) === 'admin' ? 'badge-blue' : 'badge-gray'">
                  {{ (u.permission || u.role) === 'admin' ? '管理员' : '成员' }}
                </span>
              </td>
              <td>
                <span class="badge badge-teal">{{ u.member_tier_label || '未同步' }}</span>
              </td>
              <td>{{ u.subscription_count ?? 0 }}</td>
              <td class="muted">{{ u.api_quota_used ?? 0 }} / {{ u.api_quota_total ?? 0 }}</td>
              <td>
                <span class="badge" :class="u.is_active ? 'badge-green' : 'badge-red'">
                  {{ u.is_active ? '正常' : '已禁用' }}
                </span>
              </td>
              <td class="muted">{{ fmt(u.created_at) }}</td>
              <td style="text-align: right; white-space: nowrap">
                <button class="btn btn-outline btn-sm" @click="openEdit(u)">编辑</button>
                <button class="btn btn-outline btn-sm" style="margin-left: 6px" @click="openQuota(u)">配额</button>
                <button class="btn btn-sm" style="margin-left: 6px; color: var(--danger)" @click="remove(u)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="page-actions" style="justify-content: center; margin-top: 18px">
      <button class="btn btn-outline btn-sm" :disabled="page === 1 || loading" @click="page--; load()">上一页</button>
      <span class="muted">第 {{ page }} 页</span>
      <button class="btn btn-outline btn-sm" :disabled="users.length < size || loading" @click="page++; load()">下一页</button>
    </div>

    <Modal :show="showEdit" title="编辑用户" @close="showEdit = false">
      <label class="field">
        <span>昵称</span>
        <input v-model="editForm.nickname" class="input" placeholder="用户昵称" />
      </label>
      <label class="field">
        <span>权限（不是会员档位）</span>
        <SmartSelect v-model="editForm.role" :options="[{value:'user',label:'成员'},{value:'admin',label:'管理员'}]" label="角色" />
      </label>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="editForm.is_active" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">启用该用户（关闭后禁止登录）</span>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showEdit = false">取消</button>
        <button class="btn btn-primary" :disabled="savingEdit" @click="saveEdit">
          <span v-if="savingEdit" class="spinner"></span> 保存修改
        </button>
      </div>
    </Modal>

    <Modal :show="showQuota" :title="`配额管理 - ${quotaUser?.email || ''}`" @close="showQuota = false">
      <div v-if="quotaLoading" class="loading-center">加载中…</div>
      <template v-else>
        <p class="muted" style="margin-bottom: 14px">每用户配额 · 每月自动重置</p>
        <label class="field">
          <span>配额总量</span>
          <input v-model.number="quotaForm.api_quota_total" type="number" min="0" class="input" />
        </label>
        <label class="field">
          <span>已用次数</span>
          <input v-model.number="quotaForm.api_quota_used" type="number" min="0" class="input" />
        </label>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showQuota = false">取消</button>
          <button class="btn btn-primary" :disabled="savingQuota" @click="saveQuota">
            <span v-if="savingQuota" class="spinner"></span> 保存配额
          </button>
        </div>
      </template>
    </Modal>
  </div>
</template>
