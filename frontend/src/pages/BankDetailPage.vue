<script setup>
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
import { money, riskFactors } from '../data/demo'

defineProps({ application: Object })
defineEmits(['back', 'decision'])
const decisions = [
  { code: 'approve', label: 'Одобрить', result: 'одобрено' },
  {
    code: 'counter',
    label: 'Предложить другие условия',
    result: 'другие условия',
  },
  {
    code: 'info',
    label: 'Запросить документы',
    result: 'запрошены документы',
  },
  { code: 'reject', label: 'Отказать', result: 'отказ' },
]
</script>

<template>
  <button class="link mb" @click="$emit('back')">← Все заявки</button>
  <PageHeading
    :title="`Анализ заявки ${application.id}`"
    :description="application.company"
  />
  <div class="grid3 mb">
    <div class="card">
      <div class="small muted">Сумма</div>
      <div class="stat">{{ money(application.amount) }}</div>
    </div>
    <div class="card">
      <div class="small muted">Скоринг · шкала 300–850</div>
      <div class="stat">{{ application.score }}</div>
    </div>
    <div class="card">
      <div class="small muted">Риск</div>
      <div class="stat">{{ application.risk }}</div>
    </div>
  </div>
  <div class="grid2">
    <div class="card">
      <div class="section-title">
        <h2>Что влияет на оценку</h2>
        <AppIcon name="detail" />
      </div>
      <p class="small muted">
        Иллюстрация вкладов факторов в скоринговый балл
      </p>
      <div
        v-for="factor in riskFactors"
        :key="factor.title"
        class="risk-factor"
      >
        <div class="flex">
          <span>{{ factor.title }}</span
          ><b :class="factor.impact > 0 ? 'positive' : 'red'"
            >{{ factor.impact > 0 ? '+' : '' }}{{ factor.impact }}</b
          >
        </div>
        <div class="risk-track">
          <span
            :class="{ negative: factor.impact < 0 }"
            :style="{ width: `${Math.abs(factor.impact)}%` }"
          ></span>
        </div>
      </div>
      <p class="small muted">
        ML оценивает риск, но решение принимает кредитная логика банка.
      </p>
    </div>
    <div class="card">
      <b>Решение по заявке</b>
      <p class="small muted">
        Выберите результат обработки. Пока это локальная демонстрация.
      </p>
      <div class="stack">
        <UiButton
          v-for="item in decisions"
          :key="item.code"
          :alt="item.code !== 'approve'"
          @click="$emit('decision', item.result)"
          >{{ item.label }}</UiButton
        >
      </div>
      <p class="small muted" role="status">
        {{
          application.decision
            ? `✓ Деморешение зафиксировано: ${application.decision}`
            : ''
        }}
      </p>
    </div>
  </div>
</template>
