<script setup>
import { onBeforeUnmount, ref } from 'vue'

defineProps({ alt: Boolean, type: { type: String, default: 'button' } })
const ripples = ref([])
const timers = new Set()
let sequence = 0

function ripple(event) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const bounds = event.currentTarget.getBoundingClientRect()
  const size = Math.max(bounds.width, bounds.height) * 2
  const id = sequence++
  const x =
    event.type === 'click' ? bounds.width / 2 : event.clientX - bounds.left
  const y =
    event.type === 'click' ? bounds.height / 2 : event.clientY - bounds.top
  ripples.value = [...ripples.value.slice(-2), { id, x, y, size }]
  const timer = setTimeout(() => {
    ripples.value = ripples.value.filter((item) => item.id !== id)
    timers.delete(timer)
  }, 550)
  timers.add(timer)
}
onBeforeUnmount(() => timers.forEach(clearTimeout))
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="{ alt }"
    @pointerdown="ripple"
    @click="$event.detail === 0 && ripple($event)"
  >
    <slot />
    <span
      v-for="item in ripples"
      :key="item.id"
      class="button-ripple"
      aria-hidden="true"
      :style="{
        left: `${item.x}px`,
        top: `${item.y}px`,
        width: `${item.size}px`,
        height: `${item.size}px`,
      }"
    />
  </button>
</template>
