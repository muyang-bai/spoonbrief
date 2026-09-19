<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import Modal from '../components/Modal.vue'

const reports = ref([])
const loading = ref(true)
const detail = ref(null)
const showDetail = ref(false)
const cleaning = ref(false)

const statusMap = {
  sent: { label: '已发送', cls: 'badge-green' },
  failed: { label: '失败', cls: 'badge-red' },
  fetching: { label: '抓取中', cls: 'badge-blue' },
  analyzing: { label: 'AI 分析中', cls: 'badge-blue' },
  pending: { label: '排队中', cls: 'badge-gray' },
}

// 清洗 AI 生成的 HTML：去掉 <style>/<script> 与内联样式，统一走本站样式，避免黑底等问题
function sanitizeHtml(html) {
  let s = String(html || '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<link[^>]*>/gi, '')
    .replace(/<meta[^>]*>/gi, '')
    .replace(/<!DOCTYPE[^>]*>/gi, '')
    .replace(/<html[\s\S]*?>/gi, '')
    .replace(/<\/html>/gi, '')
    .replace(/<head[\s\S]*?<\/head>/gi, '')
    .replace(/<body[^>]*>/gi, '')
    .replace(/<\/body>/gi, '')
  // 剥离所有标签属性（仅保留 <a> 的 href，且仅限 http(s)）
  s = s.replace(/<a\s+([^>]*)>/gi, (m, attrs) => {
    const href = (attrs.match(/href=["'](https?:\/\/[^"']+)["']/i) || [])[1]
    return href ? `<a href="${href}" target="_blank" rel="noopener">` : '<a>'
  })
  s = s.replace(/<(\/?)(\w+)([^>]*)>/g, '<$1$2>')
  // 若 AI 仍输出了整页样式（截断产物），判定无效
  if (/<style|<head/i.test(s)) return ''
  return s
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
  } catch (e) {
    t.err(e.message)
  }
}

async function remove(r) {
  if (!confirm('确定删除这份报告吗？')) return
  try {
    await api(`/reports/${r.id}`, { method: 'DELETE' })
    t.ok('报告已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

async function cleanup() {
  if (!confirm('将只保留最近 100 条报告，更早的会被清理，确定吗？')) return
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
      <button class="btn btn-outline btn-sm" :disabled="cleaning" @click="cleanup">
        <span v-if="cleaning" class="spinner spinner-dark"></span> 清理旧报告
      </button>
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
            <th>主题</th>
            <th>状态</th>
            <th>生成时间</th>
            <th>发送时间</th>
            <th style="width: 150px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reports" :key="r.id">
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
            <div v-for="(n, i) in relatedNews.slice(0, 20)" :key="'r' + i" class="news-item-mini" style="background: #fff7ed; border-color: #fed7aa">
              <p class="t">【{{ i + 1 }}】{{ n.title || '无标题' }}</p>
              <p class="m" v-if="n.summary">{{ n.summary.slice(0, 160) }}{{ n.summary.length > 160 ? '…' : '' }}</p>
              <p class="faint" style="margin-top: 4px">
                来源：{{ n.source || '未知' }}
                <a v-if="n.link && n.link !== '#'" :href="n.link" target="_blank" rel="noopener">原文链接</a>
                <span v-if="n.credibility"> · 可信度 {{ n.credibility }}/10</span>
                <span v-if="n._cross_validated"> · {{ n._source_count }} 源交叉验证</span>
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
                <span v-if="n._cross_validated"> · {{ n._source_count }} 源交叉验证</span>
                <span v-if="n.published"> · {{ n.published }}</span>
              </p>
            </div>
          </template>
        </template>
      </div>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showDetail = false">关闭</button>
      </div>
    </Modal>
  </div>
</template>
