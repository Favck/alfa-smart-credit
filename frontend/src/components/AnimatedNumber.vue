<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
  currency: Boolean,
  digits: { type: Number, default: 1 },
  duration: { type: Number, default: 850 },
})
const displayed = ref(props.value)
const element = ref(null)
let frame = 0
let mounted = false
let media
let observer
const format = (value) => {
  const text = Math.round(value).toLocaleString('ru-RU', {
    minimumIntegerDigits: props.digits,
  })
  return props.currency ? `${text} ₽` : text
}
const label = computed(() => format(props.value))

function animate(target, from = displayed.value) {
  cancelAnimationFrame(frame)
  if (!mounted || media?.matches || !Number.isFinite(target)) {
    displayed.value = target
    return
  }
  const started = performance.now()
  function tick(now) {
    const progress = Math.min((now - started) / props.duration, 1)
    displayed.value = from + (target - from) * (1 - (1 - progress) ** 3)
    if (progress < 1) frame = requestAnimationFrame(tick)
    else displayed.value = target
  }
  frame = requestAnimationFrame(tick)
}

function stopMotion() {
  if (media.matches) {
    cancelAnimationFrame(frame)
    displayed.value = props.value
  }
}
onMounted(() => {
  media = window.matchMedia('(prefers-reduced-motion: reduce)')
  media.addEventListener('change', stopMotion)
  const start = () => {
    mounted = true
    animate(props.value, 0)
    observer?.disconnect()
  }
  if (media.matches || !('IntersectionObserver' in window)) start()
  else {
    observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) start()
    })
    observer.observe(element.value)
  }
})
watch(
  () => props.value,
  (value) => animate(value),
)
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  media?.removeEventListener('change', stopMotion)
})
</script>

<template>
  <span ref="element" class="animated-number">
    <span class="sr-only">{{ label }}</span>
    <span aria-hidden="true">{{ format(displayed) }}</span>
  </span>
</template>
