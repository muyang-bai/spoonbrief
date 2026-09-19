<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], required: true },
  items: { type: Array, required: true },                       // 值列表（循环滚动）
  format: { type: Function, default: (v) => String(v).padStart(2, '0') },
})
const emit = defineEmits(['update:modelValue'])

const scroller = ref(null)
const ITEM_H = 40          // 每项高度
const VIEW_H = 120         // 可视高度：恰好显示 3 项
const N = props.items.length
const TRIPLED = [...props.items, ...props.items, ...props.items]

const rawIdx = ref(N)      // 当前位于三连列表中的位置（初始在中间段）
const syncing = ref(false) // 静默复位期间不回写
let scrollTimer = null

const displayItems = computed(() => TRIPLED.map((v, i) => ({ v, i })))

function actualRaw() {
  return Math.round((scroller.value?.scrollTop || 0) / ITEM_H)
}

function setPos(raw, smooth = false) {
  if (!scroller.value) return
  scroller.value.scrollTo({ top: raw * ITEM_H, behavior: smooth ? 'smooth' : 'auto' })
  rawIdx.value = raw
}

function wrappedValue(raw) {
  return props.items[((raw % N) + N) % N]
}

function recenter() {
  // 越界静默跳回中间段等价位置，实现无限循环
  const raw = rawIdx.value
  if (raw < N - 1 || raw > 2 * N - 1) {
    syncing.value = true
    const wrapped = ((raw % N) + N) % N
    setPos(N + wrapped, false)
    requestAnimationFrame(() => { syncing.value = false })
  }
}

function syncScroll() {
  const idx = props.items.indexOf(props.modelValue)
  setPos(N + (idx >= 0 ? idx : 0), false)
}

function emitValue(raw) {
  const value = wrappedValue(raw)
  if (value !== props.modelValue) emit('update:modelValue', value)
}

function onScroll() {
  if (syncing.value) return
  clearTimeout(scrollTimer)
  scrollTimer = setTimeout(() => {
    const el = scroller.value
    if (!el) return
    const raw = actualRaw()
    if (raw < N - 1 || raw > 2 * N - 1) {
      rawIdx.value = raw
      recenter()
      return
    }
    rawIdx.value = raw
    emitValue(raw)
    if (Math.abs(el.scrollTop - raw * ITEM_H) > 2) {
      setPos(raw, true)
    }
  }, 80)
}

function onWheel(e) {
  // 桌面鼠标滚轮：一格一档、即时跳格（不依赖动画，快速连滚不丢格）、循环滚动
  e.preventDefault()
  clearTimeout(scrollTimer)
  const dir = e.deltaY > 0 ? 1 : -1
  const raw = actualRaw() + dir
  if (raw < N - 1 || raw > 2 * N - 1) {
    const wrapped = ((raw % N) + N) % N
    syncing.value = true
    setPos(N + wrapped, false)
    requestAnimationFrame(() => { syncing.value = false })
    emitValue(N + wrapped)
  } else {
    setPos(raw, false)
    emitValue(raw)
  }
}

function select(v) {
  const idx = props.items.indexOf(v)
  setPos(N + idx, true)
  emit('update:modelValue', v)
}

onMounted(() => {
  nextTick(syncScroll)
  scroller.value?.addEventListener('wheel', onWheel, { passive: false })
})
onBeforeUnmount(() => {
  clearTimeout(scrollTimer)
  scroller.value?.removeEventListener('wheel', onWheel)
})
watch(() => props.modelValue, () => {
  if (!syncing.value) nextTick(syncScroll)
})
</script>

<template>
  <div ref="scroller" class="wheel-col" @scroll.passive="onScroll">
    <div class="wheel-spacer"></div>
    <div
      v-for="it in displayItems"
      :key="it.i"
      class="wheel-item"
      :class="{ active: it.i === rawIdx }"
      @click="select(it.v)"
    >{{ format(it.v) }}</div>
    <div class="wheel-spacer"></div>
  </div>
</template>

<style scoped>
.wheel-col {
  height: 120px;
  width: 110px;
  overflow-y: auto;
  scrollbar-width: none;
  text-align: center;
  cursor: grab;
  user-select: none;
  position: relative;
  border-radius: 10px;
  background: linear-gradient(
    180deg,
    rgba(249, 115, 22, 0.04) 0%,
    rgba(249, 115, 22, 0.1) 33.3%,
    rgba(249, 115, 22, 0.1) 66.6%,
    rgba(249, 115, 22, 0.04) 100%
  );
}
.wheel-col::-webkit-scrollbar { display: none; }
.wheel-spacer { height: 40px; }
.wheel-item {
  height: 40px;
  line-height: 40px;
  font-size: 16px;
  color: var(--text-faint);
  transition: color 0.15s, font-size 0.15s, font-weight 0.15s;
}
.wheel-item.active {
  color: var(--primary);
  font-weight: 800;
  font-size: 18px;
}
</style>
