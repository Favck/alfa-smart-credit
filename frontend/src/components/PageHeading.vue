<script setup>
defineProps({ title: String, description: String })
</script>

<template>
  <h1 class="heading">{{ title }}</h1>
  <p class="small muted intro">{{ description }}</p>
</template>
