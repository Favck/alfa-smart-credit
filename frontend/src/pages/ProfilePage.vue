<script setup>
import { computed } from 'vue'
import PageHeading from '../components/PageHeading.vue'
import AppIcon from '../components/AppIcon.vue'
import { money } from '../data/demo'

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
  <section class="card company-hero">
    <span class="company-emblem"><AppIcon name="profile" /></span>
    <div>
      <span class="eyebrow">ВАШ БИЗНЕС В АЛЬФА.ПОТОК</span>
      <h2>{{ profile.company }}</h2>
      <p class="muted">{{ profile.industry }}</p>
    </div>
    <span class="pill success"
      ><AppIcon name="check" />Действующая компания</span
    >
  </section>
  <div class="grid2 company-layout">
    <div class="card">
      <h3>Реквизиты и представитель</h3>
      <div v-for="[label, value] in fields" :key="label" class="line flex">
        <span class="muted">{{ label }}</span
        ><b class="text-right">{{ value }}</b>
      </div>
    </div>
    <div class="stack">
      <section class="card">
        <div class="section-title">
          <h2>Финансовые показатели</h2>
          <AppIcon name="coins" />
        </div>
        <div class="line">
          <span class="muted">Выручка в месяц</span>
          <div class="stat">{{ money(profile.revenue) }}</div>
        </div>
        <div class="line">
          <span class="muted">Текущие платежи по кредитам</span>
          <div class="stat">
            {{ money(profile.payments) }}<span class="stat-unit"> / мес.</span>
          </div>
        </div>
      </section>
      <div class="note profile-note">
        <AppIcon name="check" />
        <div>
          <b>Данные уже под рукой</b>
          <p>
            Реквизиты компании автоматически используются в новых заявках. Вам
            остаётся только рассказать о своих планах.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
