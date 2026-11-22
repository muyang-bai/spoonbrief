<script setup>
import SmartSelect from '../components/SmartSelect.vue'
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import { confirmDialog } from '../confirm'

const sources = ref([])
const customSources = ref([])
const loading = ref(true)
const adding = ref(false)
const newSource = ref({ name: '', url: '', category: '自定义' })

const typeMap = {
  rss: { label: 'RSS', cls: 'badge-teal' },
  dailyhot: { label: 'DailyHot', cls: 'badge-red' },
  newsapi: { label: 'NewsAPI', cls: 'badge-blue' },
  bing_news: { label: 'Bing', cls: 'badge-green' },
}

const categories = ['综合', '科技', '财经', '国际', '时政', '社会', '娱乐', '体育', '自定义']

async function load() {
  loading.value = true
  try {
    const [s, c] = await Promise.all([api('/sources/'), api('/sources/custom')])
    sources.value = s
    customSources.value = c
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function addCustom() {
  if (!newSource.value.name.trim()) return t.err('请填写信息源名称')
  if (!/^https?:\/\/\S+$/.test(newSource.value.url.trim())) return t.err('请输入合法的 http(s) RSS 地址')
  adding.value = true
  try {
    await api('/sources/custom', { method: 'POST', body: newSource.value })
    t.ok('自定义信息源已添加，下次简报将包含其内容')
    newSource.value = { name: '', url: '', category: '自定义' }
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    adding.value = false
  }
}

async function removeCustom(src) {
  if (!(await confirmDialog({ text: `确定删除自定义信息源「${src.name}」吗？` }))) return
  try {
    await api(`/sources/custom/${src.id}`, { method: 'DELETE' })
    t.ok('已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

function typeOf(s) {
  return typeMap[s.source_type] || { label: s.source_type || '未知', cls: 'badge-gray' }
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">平台信息源 + 你的自定义 RSS（仅用于你自己的简报）</p>
      <button class="btn btn-outline btn-sm" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner spinner-dark"></span> 刷新
      </button>
    </div>

    <!-- 我的信息源 -->
    <div class="card" style="margin-bottom: 18px">
      <h3 style="display: flex; align-items: center; justify-content: space-between; gap: 10px">
        我的信息源
        <span class="chip">{{ customSources.length }}/10</span>
      </h3>
      <p class="muted" style="margin-bottom: 12px">
        添加你自己的 RSS 订阅地址（如个人博客、垂直媒体），生成简报时会抓取并归入「与你相关」。最多 10 个，仅你本人可见。
      </p>

      <div class="toolbar" style="align-items: flex-end; flex-wrap: wrap">
        <label class="field" style="margin: 0; flex: 1; min-width: 140px">
          <span>名称</span>
          <input v-model="newSource.name" class="input" placeholder="例如：我的技术博客" />
        </label>
        <label class="field" style="margin: 0; flex: 2; min-width: 220px">
          <span>RSS 地址</span>
          <input v-model="newSource.url" class="input" placeholder="https://example.com/feed.xml" />
        </label>
        <label class="field" style="margin: 0; width: 130px">
          <span>类别</span>
          <SmartSelect v-model="newSource.category" :options="categories.map(c => ({value:c,label:c}))" label="分类" />
        </label>
        <button class="btn btn-primary" :disabled="adding" @click="addCustom">
          <span v-if="adding" class="spinner"></span> 添加
        </button>
      </div>

      <div v-if="customSources.length" style="margin-top: 14px">
        <div v-for="s in customSources" :key="s.id" style="display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px solid var(--border)">
          <div style="min-width: 0">
            <p style="font-weight: 600; font-size: 14px; margin: 0">{{ s.name }}
              <span class="badge badge-gray" style="margin-left: 6px">{{ s.category }}</span>
            </p>
            <p class="faint" style="margin: 2px 0 0; word-break: break-all">{{ s.url }}</p>
            <p class="faint" style="margin: 0">最近抓取：{{ fmtTime(s.last_fetch_at) }}<span v-if="s.last_error"> · 最近失败：{{ s.last_error }}</span></p>
          </div>
          <button class="btn btn-sm" style="color: var(--danger); flex-shrink: 0" @click="removeCustom(s)">删除</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="sources.length === 0" class="card empty">
      <div class="big">📡</div>
      <p>暂无平台信息源</p>
      <p class="muted" style="margin-top: 8px">平台尚未配置信息源，请联系管理员</p>
    </div>

    <div v-else class="grid-2">
      <div v-for="s in sources" :key="s.id" class="card">
        <h3>{{ s.name }}</h3>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px">
          <span class="badge" :class="typeOf(s).cls">{{ typeOf(s).label }}</span>
          <span class="badge badge-gray">{{ s.source_category || '综合' }}</span>
          <span class="chip">信源可信度 {{ s.credibility }}/10</span>
        </div>
        <p class="muted" style="margin-bottom: 6px; word-break: break-all">
          来源：<a :href="s.url" target="_blank" rel="noopener">{{ s.url }}</a>
        </p>
        <p class="muted" style="margin-bottom: 6px">{{ s.description || '暂无简介' }}</p>
        <p class="faint">收录时间：{{ fmtTime(s.created_at) }}</p>
      </div>
    </div>

    <p class="faint" style="margin-top: 14px; line-height: 1.8">
      关于可信度：信源可信度为 1-10 分的媒体评级（官方媒体 10 / 权威媒体 9 / 专业媒体 7 / 科技媒体 6 / 社区与自定义 4），
      用于排序参考，不代表单篇内容真实性。
    </p>
  </div>
</template>
