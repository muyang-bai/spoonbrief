<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, getToken } from '../api'
import { t } from '../toast'
import Modal from '../components/Modal.vue'
import { confirmDialog } from '../confirm'

const reports = ref([])
const loading = ref(true)
const detail = ref(null)
const showDetail = ref(false)
const viewMode = ref('email')       // email = 邮件版式（与推送一致）；raw = 原文数据
const emailHtml = ref('')
const emailLoading = ref(false)
const cleaning = ref(false)
const selected = ref([])
const allChecked = computed(() => reports.value.length > 0 && selected.value.length === reports.value.length)
function toggleAll(e) { selected.value = e.target.checked ? reports.value.map((r) => r.id) : [] }
function toggleOne(id) {
  const i = selected.value.indexOf(id)
  i >= 0 ? selected.value.splice(i, 1) : selected.value.push(id)
}

const statusMap = {
  sent: { label: '已发送', cls: 'badge-green' },
  failed: { label: '失败', cls: 'badge-red' },
  fetching: { label: '抓取中', cls: 'badge-blue' },
  analyzing: { label: 'AI 分析中', cls: 'badge-blue' },
  pending: { label: '排队中', cls: 'badge-gray' },
}

// 清洗 AI 生成的 HTML：去掉 <style>/<script> 与内联样式，统一走本站样式，避免黑底等问题
function sanitizeHtml(html) {
  const doc = new DOMParser().parseFromString(String(html || ''), 'text/html')
  for (const node of doc.querySelectorAll('script,style,head,iframe,object,embed,img,svg,math,form,video,audio')) node.remove()
  const allowed = new Set(['P','DIV','H1','H2','H3','H4','H5','H6','UL','OL','LI','STRONG','EM','B','I','SPAN','BR','BLOCKQUOTE'])
  for (const node of [...doc.body.querySelectorAll('*')]) {
    if (!allowed.has(node.tagName)) node.replaceWith(...node.childNodes)
    else for (const attr of [...node.attributes]) node.removeAttribute(attr.name)
  }
  return doc.body.innerHTML
}

const safeHtml = computed(() => (detail.value ? sanitizeHtml(detail.value.ai_analysis_html) : ''))

// 溯源新闻条目（按相关度分层：与你相关 / 今日要闻）
const newsItems = computed(() => {
  if (!detail.value || !detail.value.raw_news_json) return []
  try {
    const arr = JSON.parse(detail.value.raw_news_json)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
})

const relatedNews = computed(() => newsItems.value.filter((n) => (n.relevance || 0) > 0))
const breadthNews = computed(() => newsItems.value.filter((n) => (n.relevance || 0) <= 0))

async function load() {
  loading.value = true
  try {
    reports.value = await api('/reports/')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function openDetail(r) {
  try {
    detail.value = await api(`/reports/${r.id}`)
    showDetail.value = true
    viewMode.value = 'email'
    loadEmailHtml(r.id)
  } catch (e) {
    t.err(e.message)
  }
}

// 邮件版式：直接取后端用同一套邮件模板渲染的 HTML（与用户收到的邮件完全一致）
async function loadEmailHtml(id) {
  emailLoading.value = true
  emailHtml.value = ''
  try {
    const res = await fetch(`/api/v1/reports/${id}/email-html`, {
      headers: { Authorization: 'Bearer ' + getToken() },
    })
    emailHtml.value = res.ok ? await res.text() : ''
  } catch {
    emailHtml.value = ''
  } finally {
    emailLoading.value = false
  }
}

async function remove(r) {
  if (!(await confirmDialog({ title: '删除这份报告？', text: `「${r.subject || '未命名报告'}」删除后不可恢复。` }))) return
  try {
    await api(`/reports/${r.id}`, { method: 'DELETE' })
    t.ok('报告已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

async function removeSelected() {
  const ids = [...selected.value]
  if (!ids.length) return
  if (!(await confirmDialog({ title: '批量删除报告？', text: `将删除选中的 ${ids.length} 份报告，删除后不可恢复。` }))) return
  try {
    const res = await api('/reports/batch-delete', { method: 'POST', body: { ids } })
    t.ok(res.message || `已删除 ${res.deleted} 份`)
    selected.value = []
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

async function cleanup() {
  if (!(await confirmDialog({ title: '清理旧报告？', text: '将只保留最近 100 条报告，更早的会被清理。' }))) return
  cleaning.value = true
  try {
    const res = await api('/reports/cleanup', { method: 'POST' })
    t.ok(res.message)
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    cleaning.value = false
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
      <p class="muted">你所有的 AI 生成简报，最多保留最近 100 条</p>
      <div class="actions-right">
        <button v-if="selected.length" class="btn btn-sm" style="color: #fff; background: var(--danger)" @click="removeSelected">
          删除选中（{{ selected.length }}）
        </button>
        <button class="btn btn-outline btn-sm" :disabled="cleaning" @click="cleanup">
          <span v-if="cleaning" class="spinner spinner-dark"></span> 清理旧报告
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="reports.length === 0" class="card empty">
      <div class="big">📄</div>
      <p>暂无报告</p>
      <p class="muted" style="margin-top: 8px">创建订阅后报告将在此处自动生成</p>
    </div>

    <div v-else class="card" style="padding: 8px 4px">
      <table class="table">
        <thead>
          <tr>
            <th style="width: 44px"><input type="checkbox" :checked="allChecked" aria-label="全选" @change="toggleAll" /></th>
            <th>主题</th>
            <th>状态</th>
            <th>生成时间</th>
            <th>发送时间</th>
            <th style="width: 150px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reports" :key="r.id">
            <td><input type="checkbox" :checked="selected.includes(r.id)" :aria-label="'选择 ' + (r.subject || r.id)" @change="toggleOne(r.id)" /></td>
            <td>
              <span style="font-weight: 600; cursor: pointer" @click="openDetail(r)">{{ r.subject || '未命名报告' }}</span>
              <span v-if="r.error_message" class="badge badge-red" style="margin-left: 8px">有错误</span>
            </td>
            <td><span class="badge" :class="(statusMap[r.status] || statusMap.pending).cls">{{ (statusMap[r.status] || statusMap.pending).label }}</span></td>
            <td class="muted">{{ fmtTime(r.created_at) }}</td>
            <td class="muted">{{ fmtTime(r.sent_at) }}</td>
            <td>
              <button class="btn btn-outline btn-sm" @click="openDetail(r)">查看</button>
              <button class="btn btn-sm" style="color: var(--danger)" @click="remove(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showDetail" :title="detail?.subject || '报告详情'" width="880px" @close="showDetail = false">
      <div v-if="detail" class="report-body">
        <div style="display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap">
          <span class="badge" :class="(statusMap[detail.status] || statusMap.pending).cls">{{ (statusMap[detail.status] || statusMap.pending).label }}</span>
          <span class="badge badge-gray">生成于 {{ fmtTime(detail.created_at) }}</span>
          <span v-if="detail.sent_at" class="badge badge-gray">发送于 {{ fmtTime(detail.sent_at) }}</span>
        </div>

        <p v-if="detail.error_message" class="danger-zone" style="margin-bottom: 14px">
          <strong>错误信息：</strong>{{ detail.error_message }}
        </p>

        <div style="display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap">
          <button class="btn btn-sm" :class="viewMode === 'email' ? 'btn-primary' : 'btn-outline'" @click="viewMode = 'email'">邮件版式</button>
          <button class="btn btn-sm" :class="viewMode === 'raw' ? 'btn-primary' : 'btn-outline'" @click="viewMode = 'raw'">原文数据</button>
        </div>

        <!-- 邮件版式：与用户收到的推送邮件完全一致（同一套模板渲染） -->
        <template v-if="viewMode === 'email'">
          <div v-if="emailLoading" class="loading-center">加载邮件版式…</div>
          <iframe
            v-else-if="emailHtml"
            :srcdoc="emailHtml"
            title="邮件版式预览"
            style="width: 100%; height: 72vh; border: 1px solid var(--border); border-radius: 14px; background: #f9fafb"
          ></iframe>
          <div v-else class="empty" style="padding: 24px">
            <p class="muted">该报告暂无可预览的邮件版式（历史报告可能未保存展示数据）</p>
          </div>
        </template>

        <template v-else>
        <!-- AI 全局分析 -->
        <h4 style="font-size: 15px; margin: 6px 0 12px; color: var(--primary)">AI 全局分析</h4>
        <div v-if="safeHtml && safeHtml.trim()" class="report-html" v-html="safeHtml"></div>
        <div v-else class="empty" style="padding: 24px">
          <p class="muted">此报告暂无分析内容，可能是 AI 分析未完成或信息源无数据</p>
        </div>

        <!-- 热点分层（溯源）：与你相关 + 今日要闻 -->
        <template v-if="newsItems.length">
          <hr class="sep" />
          <template v-if="relatedNews.length">
            <h4 style="font-size: 15px; margin: 6px 0 12px; color: var(--primary)">与你相关</h4>
            <div v-for="(n, i) in relatedNews.slice(0, 20)" :key="'r' + i" class="news-item-mini" style="background: #fff7ed; border-color: #c7d2fe">
              <p class="t">【{{ i + 1 }}】{{ n.title || '无标题' }}</p>
              <p class="m" v-if="n.summary">{{ n.summary.slice(0, 160) }}{{ n.summary.length > 160 ? '…' : '' }}</p>
              <p class="faint" style="margin-top: 4px">
                来源：{{ n.source || '未知' }}
                <a v-if="n.link && n.link !== '#'" :href="n.link" target="_blank" rel="noopener">原文链接</a>
                <span v-if="n.credibility"> · 可信度 {{ n.credibility }}/10</span>
                <!-- t110：交叉验证口径修正中，暂不展示 -->
                <span v-if="n.published"> · {{ n.published }}</span>
              </p>
            </div>
          </template>
          <template v-if="breadthNews.length">
            <h4 style="font-size: 15px; margin: 18px 0 12px; color: var(--primary)">今日要闻</h4>
            <div v-for="(n, i) in breadthNews.slice(0, 20)" :key="'b' + i" class="news-item-mini">
              <p class="t">【{{ relatedNews.length + i + 1 }}】{{ n.title || '无标题' }}</p>
              <p class="m" v-if="n.summary">{{ n.summary.slice(0, 160) }}{{ n.summary.length > 160 ? '…' : '' }}</p>
              <p class="faint" style="margin-top: 4px">
                来源：{{ n.source || '未知' }}
                <a v-if="n.link && n.link !== '#'" :href="n.link" target="_blank" rel="noopener">原文链接</a>
                <span v-if="n.credibility"> · 可信度 {{ n.credibility }}/10</span>
                <!-- t110：交叉验证口径修正中，暂不展示 -->
                <span v-if="n.published"> · {{ n.published }}</span>
              </p>
            </div>
          </template>
        </template>
        </template>
      </div>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showDetail = false">关闭</button>
      </div>
    </Modal>
  </div>
</template>
