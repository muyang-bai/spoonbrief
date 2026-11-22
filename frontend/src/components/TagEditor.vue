<script setup>
import { computed, ref } from 'vue'
const props = defineProps({
  modelValue: { type: [Array, String], default: () => [] },
  options: { type: Array, default: () => [] },
  label: { type: String, required: true },
  single: Boolean,
})
const emit = defineEmits(['update:modelValue'])
const input = ref('')
const error = ref('')
const selected = computed(() => props.single ? (props.modelValue ? [props.modelValue] : []) : (Array.isArray(props.modelValue) ? props.modelValue : []))
const choices = computed(() => [...new Set([...selected.value, ...props.options])])
function toggle(value) {
  error.value = ''
  emit('update:modelValue', props.single ? (props.modelValue === value ? '' : value) : selected.value.includes(value) ? selected.value.filter(v => v !== value) : [...selected.value, value])
}
function add(event) {
  if (event?.isComposing || event?.keyCode === 229) return
  if (event?.type === 'keydown') event.preventDefault()
  const value = input.value.trim()
  if (!value) { error.value = '请先输入标签'; return }
  if (selected.value.includes(value)) { error.value = '这个标签已添加'; return }
  emit('update:modelValue', props.single ? value : [...selected.value, value])
  input.value = ''
  error.value = ''
}
</script>
<template>
  <div class="tag-editor" role="group" :aria-label="label">
    <div class="tag-choices">
      <button v-for="value in choices" :key="value" type="button" class="profile-tag" :class="{ selected: selected.includes(value) }" :aria-pressed="selected.includes(value)" :aria-label="(selected.includes(value) ? '移除' : '选择') + label + '：' + value" @click="toggle(value)">
        {{ value }} <span v-if="selected.includes(value)" aria-hidden="true">×</span>
      </button>
      <span v-if="!selected.length" class="tag-empty">尚未填写</span>
    </div>
    <div class="tag-add">
      <input v-model="input" class="input" :aria-label="'自定义' + label" :placeholder="'输入自定义' + label" maxlength="80" @keydown.enter="add($event)" />
      <button type="button" class="btn btn-outline" :aria-label="'添加' + label + '标签'" @click="add">＋ 添加标签</button>
    </div>
    <p v-if="error" class="form-error" role="status">{{ error }}</p>
  </div>
</template>
<style scoped>
.tag-choices { display:flex;flex-wrap:wrap;gap:8px; }
.profile-tag { display:inline-flex;align-items:center;gap:8px;border:1px solid #dde8f5;background:#fff;color:#60748a;border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer;overflow-wrap:anywhere;text-align:left;max-width:100%; }
.profile-tag.selected { background:#eef5ff;color:#2868ed;border-color:#bed4f1;font-weight:600; }
.profile-tag span { font-size:16px; }
.tag-empty { color:#8790A0;font-size:12px;padding:6px 0; }
.tag-add { display:flex;gap:8px;margin-top:10px; }
.tag-add input { flex:1;min-width:0;max-width:360px;font-size:13px; }
.tag-add button { flex-shrink:0;font-size:13px; }
.profile-tag:focus-visible { outline:2px solid #2868ed;outline-offset:2px; }
@media(max-width:420px) { .tag-add { flex-wrap:wrap; }.tag-add input { flex-basis:100%;max-width:none; }.tag-add button { margin-left:auto; } }
</style>
