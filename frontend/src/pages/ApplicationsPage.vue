<script setup>
import ApplicationTimeline from '../components/ApplicationTimeline.vue'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AnimatedNumber from '../components/AnimatedNumber.vue'

defineProps({
  application: Object,
  product: Object,
  stage: Number,
  profile: Object,
})
defineEmits(['stage'])
const events = [
  'Заявка отправлена',
  'Данные компании проверены',
  'Данные ЕГРЮЛ и БКИ получены',
  'Начата оценка кредитного риска',
]
</script>

<template>
  <PageHeading
    :title="
      stage === 4 ? 'Финансирование одобрено' : 'Ваши планы уже в работе'
    "
    description="Заявка APP-1042"
  />
  <div class="grid2 status-layout">
    <div class="stack">
      <div class="card status-summary">
        <div class="flex">
          <div>
            <h2>{{ product.name }}</h2>
          </div>
          <span class="pill">{{
            stage === 4
              ? 'Одобрена'
              : stage === 3
                ? 'Решение готово'
                : 'В обработке'
          }}</span>
        </div>
        <div class="status-amount">
          <AnimatedNumber :value="application.amount" currency />
        </div>
        <div class="grid2 mt">
          <div>
            <div class="small muted">Компания</div>
            <b class="small">{{ profile.company }}</b>
          </div>
          <div>
            <div class="small muted">Срок</div>
            <b class="small">{{ application.months }} мес.</b>
          </div>
        </div>
      </div>
      <div class="card">
        <b>История событий · демо</b>
        <TransitionGroup name="history" tag="div" class="history-events">
          <div
            v-for="(event, index) in events.slice(0, Math.min(stage + 1, 4))"
            :key="event"
            class="line flex"
          >
            <span>✓ {{ event }}</span
            ><span class="muted"
              >14:{{ String(3 + index * 2).padStart(2, '0') }}</span
            >
          </div>
        </TransitionGroup>
      </div>
    </div>
    <ApplicationTimeline :stage="stage" />
  </div>
  <div class="flex wrap mt start">
    <UiButton alt :disabled="stage === 0" @click="$emit('stage', stage - 1)"
      >← Предыдущий этап (демо)</UiButton
    >
    <UiButton :disabled="stage === 4" @click="$emit('stage', stage + 1)"
      >Следующий этап (демо) →</UiButton
    >
  </div>
</template>
