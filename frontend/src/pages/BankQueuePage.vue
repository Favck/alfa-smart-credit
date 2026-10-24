<script setup>
import PageHeading from '../components/PageHeading.vue'
import AppIcon from '../components/AppIcon.vue'
import { money } from '../data/demo'

defineProps({ cases: Array })
defineEmits(['open'])
</script>

<template>
  <PageHeading
    title="Кредитный конвейер"
    description="Сохранённые заявки и результаты оценки кредитного риска"
  />
  <div class="grid3 mb">
    <div class="card bank-metric">
      <span class="overview-icon"><AppIcon name="applications" /></span>
      <div>
        <div class="small muted">Всего заявок</div>
        <div class="stat">{{ cases.length }}</div>
      </div>
    </div>
    <div class="card bank-metric">
      <span class="overview-icon accent"><AppIcon name="clock" /></span>
      <div>
        <div class="small muted">На ручном рассмотрении</div>
        <div class="stat">
          {{ cases.filter((item) => item.status === 'REVIEW').length }}
        </div>
      </div>
    </div>
    <div class="card bank-metric">
      <span class="overview-icon"><AppIcon name="detail" /></span>
      <div>
        <div class="small muted">ML недоступен</div>
        <div class="stat">
          {{ cases.filter((item) => item.scoring_unavailable).length }}
        </div>
      </div>
    </div>
  </div>
  <div class="card">
    <b>Очередь заявок</b>
    <p v-if="!cases.length" class="muted mt">
      Пока нет заявок. Они появятся после создания в клиентском кабинете.
    </p>
    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Компания</th>
            <th>Сумма</th>
            <th>Скоринг</th>
            <th>Решение</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cases" :key="item.id">
            <td>
              <b>{{ item.company }}</b>
              <div class="muted">{{ item.number }}</div>
            </td>
            <td>{{ money(item.amount) }}</td>
            <td>
              <b>{{ item.score ?? '—' }}</b>
              <div>
                <span
                  class="pill"
                  :class="item.score >= 620 ? 'success' : 'pending'"
                  >{{ item.risk }}</span
                >
              </div>
            </td>
            <td>
              <span class="pill" :class="{ success: item.decision }">{{
                item.status_label
              }}</span>
            </td>
            <td>
              <button
                class="link"
                :aria-label="`Открыть заявку ${item.number}`"
                @click="$emit('open', item.id)"
              >
                Открыть →
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
