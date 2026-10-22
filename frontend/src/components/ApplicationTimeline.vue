<script setup>
import { steps } from '../data/demo'

defineProps({ stage: { type: Number, required: true } })
</script>

<template>
  <div class="card">
    <div class="flex mb">
      <b>Путь заявки</b>
      <span class="pill">
        {{
          stage === 4
            ? 'Одобрена'
            : stage === 3
              ? 'Решение готово'
              : 'В обработке'
        }}
      </span>
    </div>
    <div
      v-for="(step, index) in steps"
      :key="step.title"
      class="flow-step"
      :class="{
        done: index < stage,
        current: index === stage,
        future: index > stage,
      }"
      :aria-current="index === stage ? 'step' : undefined"
    >
      <div class="flow-rail">
        <div class="flow-circle">
          <Transition name="step" mode="out-in"
            ><span :key="index < stage ? 'done' : 'number'">{{
              index < stage ? '✓' : index + 1
            }}</span></Transition
          >
        </div>
        <div v-if="index < steps.length - 1" class="flow-line"></div>
      </div>
      <div>
        <div class="flow-title">{{ step.title }}</div>
        <div class="flow-desc">
          {{
            index === stage
              ? 'Текущий этап'
              : index < stage
                ? 'Успешно завершено'
                : 'Ожидается'
          }}
        </div>
      </div>
    </div>
    <div class="note" aria-live="polite">
      <svg class="status-check-art" viewBox="0 0 150 125" aria-hidden="true">
        <defs>
          <linearGradient id="check-red" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="#ff6958" />
            <stop offset=".6" stop-color="#ef3124" />
            <stop offset="1" stop-color="#af150c" />
          </linearGradient>
          <linearGradient id="check-metal">
            <stop stop-color="#b4b4b9" />
            <stop offset=".45" stop-color="#f5f5f6" />
            <stop offset="1" stop-color="#98989d" />
          </linearGradient>
        </defs>
        <ellipse cx="78" cy="112" rx="48" ry="8" fill="#000" opacity=".07" />
        <path d="M30 88q48-18 96 0v19q-48 18-96 0Z" fill="url(#check-metal)" />
        <ellipse cx="78" cy="88" rx="48" ry="10" fill="#eeeef0" />
        <path d="m37 57 18-17 24 23 41-49 18 17-58 64Z" fill="#b21d14" />
        <path
          d="m30 50 18-17 24 23 41-49 18 17-58 64Z"
          fill="url(#check-red)"
          stroke="#ff887c"
          stroke-width="1.5"
        />
      </svg>
      <b>Что происходит сейчас?</b>
      <Transition name="timeline-note" mode="out-in"
        ><p :key="stage">
          {{ steps[stage].description }}.
          {{
            stage < 3
              ? 'Пока никаких действий от вас не требуется.'
              : stage === 3
                ? 'Ожидайте предложение банка.'
                : 'Можно перейти к подписанию.'
          }}
        </p></Transition
      >
    </div>
  </div>
</template>
