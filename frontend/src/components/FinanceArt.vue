<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const element = ref(null)
const visible = ref(false)
const tabVisible = ref(true)
let observer
function updateVisibility() {
  tabVisible.value = !document.hidden
}
onMounted(() => {
  updateVisibility()
  document.addEventListener('visibilitychange', updateVisibility)
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(([entry]) => {
      visible.value = entry.isIntersecting
    })
    observer.observe(element.value)
  } else visible.value = true
})
onBeforeUnmount(() => {
  observer?.disconnect()
  document.removeEventListener('visibilitychange', updateVisibility)
})
</script>

<template>
  <div
    ref="element"
    class="finance-art"
    :class="{ 'is-animated': visible && tabVisible }"
    aria-hidden="true"
  >
    <img
      class="hero-art-image"
      src="/images/hero-card.png"
      alt=""
      width="1024"
      height="1024"
      fetchpriority="high"
    />
  </div>
</template>
