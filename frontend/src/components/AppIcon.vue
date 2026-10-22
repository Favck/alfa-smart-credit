<script setup>
defineProps({ name: { type: String, default: 'home' } })
const paths = {
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  products: 'M4 4h6v6H4Zm10 0h6v6h-6ZM4 14h6v6H4Zm10 0h6v6h-6Z',
  apply: 'M12 5v14M5 12h14',
  applications: 'M8 3h8l4 4v14H4V3h4Zm7 0v5h5M8 12h8m-8 4h5',
  news: 'M4 4h16v16H4Zm4 4h8m-8 4h8m-8 4h4',
  profile: 'M4 21V7l8-4 8 4v14M9 21v-5h6v5M8 9h1m6 0h1m-8 3h1m6 0h1',
  queue: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
  detail: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 6 6M7 10h6m-3-3v6',
}
</script>

<template>
  <svg
    class="app-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.65"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name] || paths.home" />
  </svg>
</template>
