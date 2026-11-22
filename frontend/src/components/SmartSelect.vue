<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
const props = defineProps({ modelValue: { default: null }, options: { type: Array, default: () => [] }, multiple: Boolean, disabled: Boolean, label: { type: String, default: '请选择' } })
const emit = defineEmits(['update:modelValue'])
const root = ref(null), trigger = ref(null), list = ref(null), open = ref(false), active = ref(0)
const id = 'choice-' + Math.random().toString(36).slice(2)
const selected = v => props.multiple ? (props.modelValue || []).includes(v) : props.modelValue === v
const text = computed(() => props.options.filter(o => selected(o.value)).map(o => o.label).join('、') || props.label)
async function show() { if (props.disabled) return; open.value = true; active.value = Math.max(0, props.options.findIndex(o => selected(o.value))); await nextTick(); list.value?.focus() }
function close(focus = false) { open.value = false; if (focus) trigger.value?.focus() }
function pick(o) { if (o.disabled) return; if (props.multiple) { const v = [...(props.modelValue || [])]; const i = v.indexOf(o.value); i < 0 ? v.push(o.value) : v.splice(i, 1); emit('update:modelValue', v) } else { emit('update:modelValue', o.value); close(true) } }
let search = '', timer
function keys(e) {
 if (e.key === 'Tab') { close(); return }
 if (e.key === 'Escape') { e.preventDefault(); close(true); return }
 if (!open.value) { if (['ArrowDown','ArrowUp','Enter',' '].includes(e.key)) { e.preventDefault(); show() }; return }
 if (['ArrowDown','ArrowUp','Home','End'].includes(e.key)) { e.preventDefault(); const n = props.options.length; if (!n) return; active.value = e.key === 'Home' ? 0 : e.key === 'End' ? n-1 : (active.value + (e.key === 'ArrowDown' ? 1 : -1) + n) % n; nextTick(() => list.value?.children[active.value]?.scrollIntoView({block:'nearest'})) }
 else if (['Enter',' '].includes(e.key)) { e.preventDefault(); const o = props.options[active.value]; if (o) pick(o) }
 else if (e.key.length === 1) { search += e.key.toLowerCase(); clearTimeout(timer); timer = setTimeout(() => { search = '' }, 700); const i = props.options.findIndex(o => String(o.label).toLowerCase().startsWith(search)); if (i >= 0) active.value = i }
}
function outside(e) { if (!root.value?.contains(e.target)) close() }
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => { document.removeEventListener('pointerdown', outside); clearTimeout(timer) })
</script>
<template>
 <div ref="root" class="smart-select" @focusout="e => { if (!root?.contains(e.relatedTarget)) close() }">
  <button ref="trigger" type="button" class="smart-trigger" role="combobox" aria-haspopup="listbox" :aria-label="label" :aria-expanded="open" :aria-controls="id" :disabled="disabled" @click="open ? close() : show()" @keydown="keys"><span>{{ text }}</span><span aria-hidden="true">⌄</span></button>
  <div v-if="open" :id="id" ref="list" role="listbox" :aria-label="label" :aria-multiselectable="multiple || undefined" :aria-activedescendant="id + '-' + active" tabindex="0" class="smart-options" @keydown="keys">
   <div v-for="(o,i) in options" :id="id + '-' + i" :key="i" role="option" :aria-selected="selected(o.value)" :aria-disabled="!!o.disabled" :class="['smart-option', {selected: selected(o.value), active:i === active, disabled:o.disabled}]" @pointermove="active=i" @mousedown.prevent @click="pick(o)"><span>{{ o.label }}</span><span v-if="selected(o.value)" aria-hidden="true">✓</span></div>
   <p v-if="!options.length" class="muted">暂无选项</p>
  </div>
 </div>
</template>
<style scoped>
.smart-select{position:relative;width:100%;min-width:0;font-size:14px}.smart-trigger{width:100%;min-height:44px;border:1px solid #dde8f5;border-radius:12px;background:#fff;color:#18304a;padding:10px 13px;display:flex;justify-content:space-between;gap:14px;align-items:center;font:inherit;text-align:left;cursor:pointer}.smart-trigger span:first-child{overflow-wrap:anywhere}.smart-trigger:hover{border-color:#2868ed}.smart-trigger:focus-visible,.smart-options:focus-visible{outline:2px solid #2868ed;outline-offset:2px}.smart-trigger:disabled{opacity:.55;cursor:not-allowed}.smart-options{position:absolute;top:calc(100% + 6px);left:0;right:0;z-index:90;max-height:min(260px,45vh);overflow:auto;overscroll-behavior:contain;border:1px solid #dde8f5;background:#fff;border-radius:14px;padding:5px;box-shadow:0 14px 35px #18304a1a}.smart-option{padding:10px 12px;border-radius:9px;min-height:42px;cursor:pointer;display:flex;justify-content:space-between;gap:12px;overflow-wrap:anywhere}.smart-option.active{background:#eef5ff}.smart-option.selected{color:#1859dc;font-weight:600}.smart-option.disabled{opacity:.5;cursor:not-allowed}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style>
