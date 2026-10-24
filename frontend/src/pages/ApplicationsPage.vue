<script setup>
import PageHeading from '../components/PageHeading.vue'
import AppIcon from '../components/AppIcon.vue'
import UiButton from '../components/UiButton.vue'
import { money, products } from '../data/demo'
defineProps({
  applications: Array,
  application: Object,
  history: Array,
  busy: Boolean,
})
defineEmits(['open', 'refresh', 'create', 'submit', 'cancel'])
const productName = (id) => products.find((p) => p.id === id)?.name || id
const date = (value) => new Date(value).toLocaleString('ru-RU')
</script>
<template>
  <PageHeading
    title="Мои заявки"
    description="Сохранённые обращения, результаты оценки и история рассмотрения"
  />
  <div class="flex wrap mb">
    <UiButton @click="$emit('create')"
      ><AppIcon name="apply" />Новая заявка</UiButton
    ><UiButton alt :disabled="busy" @click="$emit('refresh')"
      >Обновить</UiButton
    >
  </div>
  <section v-if="!applications.length" class="card empty-state">
    <AppIcon name="applications" />
    <h2>Пока нет заявок</h2>
    <p class="muted">
      Выберите продукт и расскажите о потребности вашего бизнеса.
    </p>
  </section>
  <div v-else class="grid2 saved-app-layout">
    <div class="stack">
      <button
        v-for="item in applications"
        :key="item.id"
        class="card saved-application"
        :class="{ selected: application?.id === item.id }"
        :aria-label="`Открыть заявку ${item.number}`"
        @click="$emit('open', item.id)"
      >
        <div class="flex wrap">
          <b>{{ item.number }}</b
          ><span
            class="pill"
            :class="{
              success: item.status === 'APPROVED',
              pending: item.status === 'REVIEW',
            }"
            >{{ item.status_label }}</span
          >
        </div>
        <h3>{{ productName(item.productId) }}</h3>
        <div class="stat">{{ money(item.amount) }}</div>
        <p class="muted small">
          {{ item.months }} мес. · {{ date(item.created_at) }}
        </p>
        <span class="link">Открыть заявку →</span>
      </button>
    </div>
    <section v-if="application" class="card application-detail">
      <span class="eyebrow">{{ application.number }}</span>
      <h2>{{ application.status_label }}</h2>
      <p class="muted">
        {{ productName(application.productId) }} ·
        {{ money(application.amount) }} · {{ application.months }} мес.
      </p>
      <div class="note">
        <b>{{ application.client_scoring?.risk_label }}</b>
        <p>{{ application.client_scoring?.explanation }}</p>
        <ul v-if="application.client_scoring?.reasons.length">
          <li
            v-for="reason in application.client_scoring.reasons"
            :key="reason"
          >
            {{ reason }}
          </li>
        </ul>
      </div>
      <div class="line">
        <span class="muted">Цель финансирования</span>
        <p>{{ application.purpose || 'Не указана' }}</p>
      </div>
      <div class="flex wrap mt">
        <UiButton
          v-if="['DRAFT', 'SCORING'].includes(application.status)"
          :disabled="busy"
          @click="$emit('submit', application.id)"
          >{{
            application.status === 'DRAFT'
              ? 'Отправить на рассмотрение'
              : 'Повторить обработку'
          }}</UiButton
        ><UiButton
          v-if="['DRAFT', 'REVIEW'].includes(application.status)"
          alt
          :disabled="busy"
          @click="$emit('cancel', application.id)"
          >Отменить заявку</UiButton
        >
      </div>
      <p v-if="application.status === 'APPROVED'" class="muted small mt">
        Оценка завершена. Предложение банка, договор и подписание — следующий
        этап проекта.
      </p>
      <h3 class="mt">История заявки</h3>
      <p v-if="!history.length" class="muted small">
        Выберите заявку в списке, чтобы загрузить историю.
      </p>
      <ol class="event-list">
        <li v-for="event in history" :key="event.id">
          <span class="event-dot"></span>
          <div>
            <b>{{ event.message }}</b>
            <p class="muted small">
              {{ date(event.created_at) }} ·
              {{
                {
                  system: 'Система',
                  client: 'Клиент',
                  bank: 'Сотрудник банка',
                }[event.actor_role]
              }}
            </p>
          </div>
        </li>
      </ol>
    </section>
  </div>
</template>
