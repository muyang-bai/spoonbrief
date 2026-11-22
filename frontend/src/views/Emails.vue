<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import { confirmDialog } from '../confirm'
import Modal from '../components/Modal.vue'

const emails = ref([])
const loading = ref(true)

const showAdd = ref(false)
const addForm = ref({ email: '' })
const adding = ref(false)

const sendingId = ref(null)
const deletingId = ref(null)

const verifyTarget = ref(null)
const verifyCode = ref('')
const showVerify = ref(false)
const verifying = ref(false)

async function load() {
  loading.value = true
  try {
    emails.value = []
    const saved = await api('/emails/')
    emails.value = saved
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openAdd() {
  addForm.value.email = ''
  showAdd.value = true
}

async function addEmail() {
  const email = addForm.value.email.trim()
  if (!email) return t.err('请输入邮箱地址')
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return t.err('邮箱格式不正确')
  adding.value = true
  try {
    await api('/emails/', { method: 'POST', body: { email } })
    t.ok('收件邮箱已添加')
    showAdd.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    adding.value = false
  }
}

async function sendCode(em) {
  sendingId.value = em.id
  try {
    const res = await api(`/emails/${em.id}/send-verify`, { method: 'POST' })
    t.ok(res.message || '验证码已提交发送，请查收')
  } catch (e) {
    t.err(e.message)
  } finally {
    sendingId.value = null
  }
}

function openVerify(em) {
  verifyTarget.value = em
  verifyCode.value = ''
  showVerify.value = true
}

function onCodeInput() {
  verifyCode.value = verifyCode.value.replace(/\D/g, '').slice(0, 6)
}

async function submitVerify() {
  if (!verifyTarget.value) return
  if (!/^\d{6}$/.test(verifyCode.value)) return t.err('请输入 6 位数字验证码')
  verifying.value = true
  try {
    const res = await api(`/emails/${verifyTarget.value.id}/verify`, { method: 'POST', params: { code: verifyCode.value } })
    t.ok(res.message || '邮箱验证成功')
    showVerify.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    verifying.value = false
  }
}

async function removeEmail(em) {
  if (!(await confirmDialog({ text: `确定删除收件邮箱「${em.email}」吗？` }))) return
  deletingId.value = em.id
  try {
    const res = await api(`/emails/${em.id}`, { method: 'DELETE' })
    t.ok(res.message || '收件邮箱已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <div><p class="muted">管理情报简报的接收邮箱（最多 3 个）</p><p class="muted">主收件邮箱使用当前账号邮箱，验证后接收简报；额外邮箱保持独立。</p></div>
      <button class="btn btn-primary" :disabled="emails.length >= 3" @click="openAdd">＋ 添加邮箱</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="emails.length === 0" class="card empty">
      <div class="big">📧</div>
      <p>还没有收件邮箱</p>
      <p class="muted" style="margin: 8px 0 16px">添加邮箱后，简报将按时送达你的收件箱</p>
      <button class="btn btn-primary" @click="openAdd">添加邮箱</button>
    </div>

    <div v-else class="card" style="padding: 8px 4px">
      <table class="table">
        <thead>
          <tr>
            <th>邮箱</th>
            <th>状态</th>
            <th style="width: 280px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="em in emails" :key="em.id">
            <td>
              <span style="font-weight: 600">{{ em.email }}</span>
              <p v-if="em.is_primary" class="faint">账号邮箱 · 主收件地址</p>
            </td>
            <td>
              <span v-if="em.is_primary" class="badge" style="margin-right: 6px">主邮箱</span>
              <span v-if="em.is_verified" class="badge badge-green">已验证</span>
              <span v-else class="badge badge-gray">未验证</span>
            </td>
            <td>
              <template v-if="!em.is_verified">
                <button class="btn btn-outline btn-sm" :disabled="sendingId === em.id" @click="sendCode(em)">
                  <span v-if="sendingId === em.id" class="spinner spinner-dark"></span> 发送验证码
                </button>
                <button class="btn btn-teal btn-sm" @click="openVerify(em)">验证邮箱</button>
              </template>
              <button v-if="!em.is_primary" class="btn btn-sm" style="color: var(--danger)" :disabled="deletingId === em.id" @click="removeEmail(em)">
                <span v-if="deletingId === em.id" class="spinner spinner-dark"></span> 删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showAdd" title="添加邮箱" @close="showAdd = false">
      <label class="field">
        <span>邮箱地址</span>
        <input v-model="addForm.email" type="email" class="input" placeholder="输入邮箱地址" @keyup.enter="addEmail" />
      </label>
      <p class="muted">邮件地址仅用于发送简报，不会用于营销或共享给第三方</p>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showAdd = false">取消</button>
        <button class="btn btn-primary" :disabled="adding" @click="addEmail">
          <span v-if="adding" class="spinner"></span> 添加
        </button>
      </div>
    </Modal>

    <Modal :show="showVerify" title="验证邮箱" @close="showVerify = false">
      <p class="muted" style="margin-bottom: 12px">
        请输入发送至 <strong>{{ verifyTarget?.email }}</strong> 的 6 位验证码
      </p>
      <input
        v-model="verifyCode"
        class="input"
        inputmode="numeric"
        maxlength="6"
        placeholder="请输入 6 位验证码"
        style="letter-spacing: 10px; text-align: center; font-size: 18px"
        @input="onCodeInput"
        @keyup.enter="submitVerify"
      />
      <div class="modal-actions">
        <button class="btn btn-outline btn-sm" :disabled="!verifyTarget || sendingId === verifyTarget.id" @click="sendCode(verifyTarget)">
          <span v-if="verifyTarget && sendingId === verifyTarget.id" class="spinner spinner-dark"></span> 重新发送验证码
        </button>
        <button class="btn btn-outline" @click="showVerify = false">取消</button>
        <button class="btn btn-primary" :disabled="verifying" @click="submitVerify">
          <span v-if="verifying" class="spinner"></span> 确认验证
        </button>
      </div>
    </Modal>
  </div>
</template>
