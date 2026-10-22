<script setup>
import { computed } from 'vue'
import PageHeading from '../components/PageHeading.vue'

const props = defineProps({ profile: Object })
const fields = computed(() => [
  ['ИНН', props.profile.inn],
  ['ОГРН / ОГРНИП', props.profile.ogrn],
  ['Статус', 'Действующая'],
  ['Отрасль', props.profile.industry],
  ['Представитель', props.profile.fullName],
  ['Роль', 'Собственник'],
])
</script>

<template>
  <PageHeading
    title="Моя компания"
    description="Профиль автоматически используется в заявках"
  />
  <div class="card">
    <h3>{{ profile.company }}</h3>
    <div v-for="[label, value] in fields" :key="label" class="line flex">
      <span class="muted">{{ label }}</span
      ><b class="text-right">{{ value }}</b>
    </div>
  </div>
</template>
